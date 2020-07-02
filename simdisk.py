import os, math, struct, time, json
import numpy as np
import time 

class Bitmap(object):
    def __init__(self, n):
        num = n/32 if n%32==0 else math.ceil(n/32)
        self._map = np.zeros(int(num),dtype=np.uint32)
        self._next_pos = 0
        self._total = n
        self._used = 0
        self._size = int(num * 4) # bytes

    def _tran_pos(self, n):
        sector = int(n/32 if n%32 == 0 else math.floor(n/32))
        offset = n - sector * 32
        return sector, offset

    def set(self,pos,value=True):
        sector, offset = self._tran_pos(pos)
        ori_val = self._map[sector]
        if value:
            new_val = self._map[sector] | (1<<offset)
        else:
            new_val = self._map[sector] & (~(1<<offset))
        if not ori_val == new_val:
            self._used += 1 if value else -1
        self._map[sector] = new_val

    def flip(self,pos):
        self.set(pos, not self.get(pos))

    def get(self,pos):
        sector, offset = self._tran_pos(pos)
        return self._map[sector] >> offset & 1

    def next(self):
        if not self._used < self._total:
            return -1
        while self.get(self._next_pos):
            self._next_pos += 1
            if not self._next_pos < self._total:
                self._next_pos -= self._total
        self.set(self._next_pos)
        return self._next_pos

class Superblock(object):
    def __init__(self,
        inode_num=102400,
        inode_struct_size=32,
        block_struct_size=1024,
        dir_region_pos = 32*1024):

        self._size = 32 * 1024 # Padding for unknown blocks num
        #self._size = self._inode_map._size + self._block_map._size + 7 * 4
        self._dir_region_pos = self._size
        self._inode_region_pos = self._dir_region_pos + 4096 * 1024
        self._block_region_pos = self._inode_region_pos + 1024 * 1024

        self._inode_num = inode_num
        self._inode_struct_size = inode_struct_size
        self._inode_map = Bitmap(inode_num)

        self._block_num = (100 * 1024 * 1024 - self._block_region_pos) >> 10
        self._block_struct_size = block_struct_size
        self._block_map = Bitmap(self._block_num)
        
    
    def encode_into(self,btarr,offset=0):
        struct.pack_into('I',btarr,offset,self._inode_map._size)
        offset += 4
        for v in self._inode_map._map:
            struct.pack_into('I',btarr,offset,v)
            offset += 4
        struct.pack_into('I',btarr,offset,self._inode_region_pos)
        offset += 4
        struct.pack_into('I',btarr,offset,self._inode_struct_size)
        offset += 4

        struct.pack_into('I',btarr,offset,self._block_map._size)
        offset += 4
        for v in self._block_map._map:
            struct.pack_into('I',btarr,offset,v)
            offset += 4
        struct.pack_into('I',btarr,offset,self._block_region_pos)
        offset += 4
        struct.pack_into('I',btarr,offset,self._block_struct_size)
        offset += 4

        struct.pack_into('I',btarr,offset,self._dir_region_pos)
        offset += 4
        return offset

    @classmethod
    def decode_from(cls,btarr,offset=0):
        blk = Superblock()
        map_size = struct.unpack_from('I',btarr,offset)[0] >> 2
        offset += 4
        for i in range(map_size):
            blk._inode_map._map[i] = struct.unpack_from('I',btarr,offset)[0]
            offset += 4
        for i in range(blk._inode_num):
            if blk._inode_map.get(i):
                blk._inode_map._used += 1
        blk._inode_region_pos = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        blk._inode_struct_size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        
        map_size = struct.unpack_from('I',btarr,offset)[0] >> 2
        offset += 4
        for i in range(map_size):
            blk._block_map._map[i] = struct.unpack_from('I',btarr,offset)[0]
            offset += 4
        for i in range(blk._block_num):
            if blk._block_map.get(i):
                blk._block_map._used += 1
        blk._block_region_pos = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        blk._block_struct_size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        
        blk._dir_region_pos = struct.unpack_from('I',btarr,offset)[0]
        offset += 4

        return blk


class DirItem(object):
    def __init__(self, name="/", inode=0):
        self._name = name
        self._inode = inode
        self._list = []

    def size(self):
        return 40 + 36 * len(self._list)

    def encode_into(self,btarr,offset=0):
        struct.pack_into('32s',btarr,offset,self._name.encode('utf-8'))
        offset += 32
        struct.pack_into('I',btarr,offset,self._inode)
        offset += 4
        struct.pack_into('I',btarr,offset,len(self._list))
        offset += 4
        for i in self._list:
            struct.pack_into('32s',btarr,offset,i['name'].encode('utf-8'))
            offset += 32
            struct.pack_into('I',btarr,offset,i['inode'])
            offset += 4
        return offset
    
    @classmethod
    def decode_from(cls,btarr,offset=0):
        name = struct.unpack_from('32s',btarr,offset)[0].decode('utf-8').strip(b'\x00'.decode())
        offset += 32
        inode = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        d = DirItem(name, inode)
        size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        for i in range(size):
            name = struct.unpack_from('32s',btarr,offset)[0].decode('utf-8').strip(b'\x00'.decode())
            offset += 32
            inode = struct.unpack_from('I',btarr,offset)[0]
            offset += 4
            d._list.append({"name":name,'inode':inode})
        return d


class INode():
    def __init__(self, perm="1100", uid=0):  
        current = time.time()
        self._perm = perm  # OwnerRead OwnerWrite OthersRead OthersWrite
        self._owner = uid        # OwnerId
        self._create_time = current
        self._access_time = current
        self._modify_time = current
        self._size = 0
        self._block = 0
        self._index = 0

    def encode_into(self,btarr,offset=0):
        struct.pack_into('4s',btarr,offset,self._perm.encode('utf-8'))
        offset += 4
        struct.pack_into('I',btarr,offset,self._owner)
        offset += 4
        struct.pack_into('f',btarr,offset,self._create_time)
        offset += 4
        struct.pack_into('f',btarr,offset,self._access_time)
        offset += 4
        struct.pack_into('f',btarr,offset,self._modify_time)
        offset += 4
        struct.pack_into('I',btarr,offset,self._size)
        offset += 4
        struct.pack_into('I',btarr,offset,self._block)
        offset += 4
        struct.pack_into('I',btarr,offset,self._index)
        offset += 4
        return offset

    @classmethod        
    def decode_from(self,btarr,offset=0):
        iN = INode()
        iN._perm = struct.unpack_from('4s',btarr,offset)[0].decode('utf-8').strip(b'\x00'.decode())
        offset += 4
        iN._owner = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        iN._create_time = struct.unpack_from('f',btarr,offset)[0]
        offset += 4
        iN._access_time = struct.unpack_from('f',btarr,offset)[0]
        offset += 4
        iN._modify_time = struct.unpack_from('f',btarr,offset)[0]
        offset += 4
        iN._size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        iN._block = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        iN._index = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        return iN
     

class Block(object):
    def __init__(self, size=1024):
        self._bytes = bytearray(size)
        self._size = size

    def encode_into(self,btarr,offset=0):
        struct.pack_into(str(self._size)+'s',btarr,offset,self._bytes)

    @classmethod
    def decode_from(cls,btarr,offset=0):
        b = Block()
        b._bytes = bytearray(struct.unpack_from(str(b._size)+'s',btarr,offset)[0])
        return b

env = {}
env['user'] = "guest"
env['path'] = "/"

class FileSystem(object):
    def __init__(self):
        self._openings = {}
        self._usertable = {}
        self._usertable['system'] = 0
        self._usertable['guest'] = 1
        if os.path.exists('diskfile'):
            _buffer = bytearray(open('diskfile', 'rb').read())
            self._super_block = Superblock.decode_from(_buffer)

            self._dirs = []
            offset = self._super_block._dir_region_pos
            while True:
                ditem = DirItem.decode_from(_buffer,offset)
                if ditem._name == "":
                    break
                self._dirs.append(ditem)
                offset += ditem.size()
            
            self._inodes = {}
            offset = self._super_block._inode_region_pos
            for i in range(self._super_block._inode_num):
                if (self._super_block._inode_map.get(i)):
                    inode = INode.decode_from(_buffer,offset+i*self._super_block._inode_struct_size)
                    self._inodes[i] = inode

            self._blocks = {}
            offset = self._super_block._block_region_pos
            for i in range(self._super_block._block_num):
                if (self._super_block._block_map.get(i)):
                    block = Block.decode_from(_buffer,offset+i*self._super_block._block_struct_size)
                    self._blocks[i] = block

            exi, inode_id = self._find("accounts")
            if exi:
                env['user'] = 'system'
                self._usertable = json.loads(self.read_file("accounts", False))
                env['user'] = 'guest'
        else:
            _buffer = bytearray(100 * 1024 * 1024)
            self._super_block = Superblock()
            self._super_block.encode_into(_buffer)
            self._dirs, self._inodes, self._blocks = [], {}, {}

            # Create root
            inode_id = self._super_block._inode_map.next()
            ditem = DirItem('/', inode_id)
            self._dirs.append(ditem)

            inode = INode()
            self._inodes[inode_id] = inode
            self.save()

    def save(self):
        _buffer = bytearray(100 * 1024 * 1024)
        self._super_block.encode_into(_buffer)

        offset = self._super_block._dir_region_pos
        for ditem in self._dirs:
            offset = ditem.encode_into(_buffer, offset)

        offset = self._super_block._inode_region_pos
        for k, v in self._inodes.items():
            v.encode_into(_buffer,offset+k*self._super_block._inode_struct_size)

        offset = self._super_block._block_region_pos
        for k, v in self._blocks.items():
            v.encode_into(_buffer,offset+k*self._super_block._block_struct_size)

        open('diskfile', 'wb').write(_buffer)

    def _find(self, name):
        for ditem in self._dirs:
            if ditem._name == env['path']:
                inode_id = [i['inode'] for i in ditem._list if i['name'] == name]
                if not inode_id:
                    return False, None
                else:
                    return True, inode_id[0]

    def _find_dir(self, name):
        for ditem in self._dirs:
            if ditem._name == name:
                return ditem._inode
        return None

    def test_perm(self, uname, inode, read=False,write=False):
        fuid = inode._owner
        owner = False
        if uname in self._usertable.keys():
            owner = True if self._usertable[uname] == inode._owner else False
        result = True
        if owner:
            if read:
                result &= inode._perm[0] == '1'
            if write:
                result &= inode._perm[1] == '1'
        else:
            if read:
                result &= inode._perm[2] == '1'
            if write:
                result &= inode._perm[3] == '1'
        return result

    def create_file(self, name):
        # 检查当前目录的写权限
        dinode = self._inodes[self._find_dir(env['path'])]
        perm = self.test_perm(env['user'],dinode,write=True)
        if not perm:
            print("Permission denied.")
            return

        exi, inode_id = self._find(name)
        if exi:
            print('File already exists:' + name)
            return
        
        for ditem in self._dirs:
            if ditem._name == env['path']:
                inode_id = self._super_block._inode_map.next()
                inode = INode('1100',self._usertable[env['user']])
                self._inodes[inode_id] = inode
                ditem._list.append({'name':name, 'inode':inode_id})
                self.save()
                return inode_id

    def write_file(self, name, data):
        exi, inode_id = self._find(name)
        if not exi:
            print('File not found :' + name)
            return

        inode = self._inodes[inode_id]
        perm = self.test_perm(env['user'],inode,write=True)
        if not perm:
            print("Permission denied.")
            return

        inode._modify_time = time.time()
        if inode._size > 0:
            block = self._blocks[inode._block]
        else:
            block_id = self._super_block._block_map.next()
            inode._block = block_id
            block = self._blocks[block_id] = Block()
        struct.pack_into(str(len(data))+'s',block._bytes,inode._size,data.encode('utf-8'))
        inode._size += np.array(len(data),dtype=np.uint32)
        self.save()

    def read_file(self, name, echo=True):
        exi, inode_id = self._find(name)
        if not exi:
            print('File not found :' + name)
            return

        inode = self._inodes[inode_id]
        perm = self.test_perm(env['user'],inode,read=True)
        if not perm:
            print("Permission denied.")
            return

        inode._access_time = time.time()
        if inode._size > 0:
            block = self._blocks[inode._block]
            data = struct.unpack_from(str(inode._size)+'s',block._bytes)[0].decode('utf-8')
            if echo:
                print(data)
            else:
                return data
        else:
            print('Empty file.')
        self.save()
    
    def list_dir(self):
        uid2user = dict([(v,k) for (k,v) in self._usertable.items()])
        mask = '{:<16}{:<8}{:>8}{:>8}{:>20}{:>20}{:>20}{:>12}'
        tmask = '%y-%m-%d %H:%M:%S'
        print(mask.format('filename', 'owner', 'perms', 'size', 'create', 'access', 'modify', 'phys_addr'))
        print('='*112)
        for ditem in self._dirs:
            if ditem._name == env['path']:
                inode = self._inodes[ditem._inode]
                ctime = time.strftime(tmask, time.localtime(inode._create_time))
                atime = time.strftime(tmask, time.localtime(inode._access_time))
                mtime = time.strftime(tmask, time.localtime(inode._modify_time))
                addr = ""
                print(mask.format(ditem._name, uid2user[inode._owner], inode._perm, "Folder",ctime, atime, mtime, addr))

                for fitem in ditem._list:
                    inode = self._inodes[fitem['inode']]
                    ctime = time.strftime(tmask, time.localtime(inode._create_time))
                    atime = time.strftime(tmask, time.localtime(inode._access_time))
                    mtime = time.strftime(tmask, time.localtime(inode._modify_time))
                    fname = (ditem._name + '/' + fitem['name']).replace('//','/')
                    (size, addr) = ("Folder", '') if self._find_dir(fname) else (inode._size, self._super_block._block_region_pos + self._super_block._block_struct_size * inode._block)
                    print(mask.format(fname, uid2user[inode._owner], inode._perm, size,ctime, atime, mtime, addr))

    def delete_file(self, name):
        # 检查当前目录的写权限
        dinode = self._inodes[self._find_dir(env['path'])]
        perm = self.test_perm(env['user'],dinode,write=True)
        if not perm:
            print("Permission denied.")
            return
    
        exi, inode_id = self._find(name)
        if not exi:
            print('File not found :' + name)
            return

        if inode_id in self._openings.keys() and len(self._openings[inode_id]) > 0:
            print('Failed, opening by {} user(s).'.format(len(self._openings[inode_id])))
            return
        else:
            for ditem in self._dirs:
                if ditem._name == env['path']:
                    inode = self._inodes[inode_id]
                    if inode._size > 0:
                        self._super_block._block_map.flip(inode._block)
                    self._super_block._inode_map.flip(inode_id)
                    ditem._list = [l for l in ditem._list if l['name'] != name]
                    self.save()

    def open_file(self, name):
        exi, inode_id = self._find(name)
        if not exi:
            print('File not found :' + name)
            return

        inode = self._inodes[inode_id]
        perm = self.test_perm(env['user'],inode,read=True)
        if not perm:
            print("Permission denied.")
            return

        uid = self._usertable[env['user']]
        if inode_id in self._openings.keys():
            self._openings[inode_id].add(uid)
        else:
            self._openings[inode_id]=set([uid])

    def close_file(self, name):
        exi, inode_id = self._find(name)
        if not exi:
            print('File not found :' + name)
            return
        uid = self._usertable[env['user']]
        if inode_id in self._openings.keys():
            self._openings[inode_id].remove(uid)

    def add_user(self, name):
        user = env['user']
        self.login('system')
        exi, inode_id = self._find("accounts")
        if exi:
            self._openings[inode_id] = set()
            self.delete_file('accounts')
        self.create_file('accounts')
        nuid = max([self._usertable[v] for v in self._usertable.keys()]) + 1
        self._usertable[name] = nuid
        self.write_file('accounts', json.dumps(self._usertable))

        inode_id = self._super_block._inode_map.next()
        self._dirs.append(DirItem('/'+name, inode_id))
        inode = INode()
        inode._owner = nuid
        self._inodes[inode_id] = inode

        for ditem in self._dirs:
            if ditem._name == '/':
                ditem._list.append({'name':name,'inode':inode_id})

        self.login(user)
        self.save()

    def login(self, name):
        if name in self._usertable.keys():
            env['user'] = name
        else:
            print("Unknown username:",name)

    def logout(self):
        env['user'] = 'guest'

    def copy_file(self, src, dst):
        exi, inode_id = self._find(src)
        if not exi:
            print('File not found :' + src)
            return

        exi, inode_id = self._find(dst)
        if exi:
            print('File already exists:' + dst)
            return

        self.create_file(dst)
        self.write_file(dst,self.read_file(src,False))

    def change_dir(self, name):
        if name == '..':
            env['path'] = '/'
            return
        else:
            if self._find_dir('/'+name):
                dinode = self._inodes[self._find_dir('/'+name)]
                perm = self.test_perm(env['user'],dinode,read=True)
                if not perm:
                    print("Permission denied.")
                    return
                env['path'] = '/'+name
                return
        print("Folder not found:",name)
    
    def info(self):
        print('Simple Filesystem ver 1.0')
        print('{:<24}{:<24}{:<24}{:<24}'.format(
            'SuperblockSize: {}B'.format(self._super_block._size),
            'DirItemsSize: {}B'.format(self._super_block._inode_region_pos - self._super_block._dir_region_pos),
            'INodeSize: {}B'.format(self._super_block._inode_struct_size),
            'BlockSize: {}B'.format(self._super_block._block_struct_size),
            ))
        print('{:<24}{:<24}{:<24}{:<24}'.format(
            'DirNum: {}'.format(len(self._dirs)),
            'INodeNum: {}'.format(self._super_block._inode_map._used),
            'BlockNum: {}'.format(self._super_block._block_map._used),
            'FileNum: {}'.format(self._super_block._inode_map._used - len(self._dirs))
            ))
        print('{:<24}{:<24}'.format(
            'MaxFile: {}'.format(min(self._super_block._inode_map._total,self._super_block._block_map._total)),
            'BiggestFile: {}B'.format(1024 + 1024 << 8),
            'UsedSpace: {}%'.format(int(self._super_block._block_map._used / self._super_block._block_map._total * 100)),
            ))
        print()

fsys = FileSystem()

func = {}
func['exit'] = exit
func['echo'] = print
func['info'] = fsys.info
func['adduser'] = fsys.add_user
func['login'] = fsys.login
func['logout'] = fsys.logout
func['open'] = fsys.open_file
func['close'] = fsys.close_file
func['create'] = fsys.create_file
func['delete'] = fsys.delete_file
func['read'] = fsys.read_file
func['write'] = fsys.write_file
func['copy'] = fsys.copy_file
func['cd'] = fsys.change_dir
func['dir'] = func['ls'] = fsys.list_dir

def main():
    while True:
        print("{}@simdisk {} $ ".format(env['user'], env['path']), end="")
        cmd = input().strip().split(' ')
        if cmd[0] == '':
            continue
        if not cmd[0] in func.keys():
            print("Unknown command: {}".format(cmd[0]))
            continue
        '''
        if len(cmd) > 1:
            func[cmd[0]](*cmd[1:])
        else:
            func[cmd[0]]()
        '''
        try:
            if len(cmd) > 1:
                func[cmd[0]](*cmd[1:])
            else:
                func[cmd[0]]()
        except BaseException as e:
            if type(e) == SystemExit:
                exit()
            print('Failed:', e)


if __name__ == "__main__":
    main()
