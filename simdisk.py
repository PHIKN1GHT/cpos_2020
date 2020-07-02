import os, math, struct
import numpy as np
import time
import struct

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
        return self._next_pos

class Superblock(object):
    def __init__(self,
        inode_num=102400,
        block_num=102400,
        inode_struct_size=32,
        block_struct_size=1024,
        dir_region_pos = 32*1024):

        self._inode_num = inode_num
        self._block_num = block_num
        self._inode_struct_size = inode_struct_size
        self._block_struct_size = block_struct_size
        self._inode_map = Bitmap(inode_num)
        self._block_map = Bitmap(block_num)
        #self._size = self._inode_map._size + self._block_map._size + 7 * 4
        self._size = 32 * 1024
        self._dir_region_pos = self._size
        self._inode_region_pos = self._dir_region_pos + 4096 * 1024
        self._block_region_pos = self._inode_region_pos + 1024 * 1024
    
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
        blk._inode_region_pos = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        blk._inode_struct_size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        
        map_size = struct.unpack_from('I',btarr,offset)[0] >> 2
        offset += 4
        for i in range(map_size):
            blk._block_map._map[i] = struct.unpack_from('I',btarr,offset)[0]
            offset += 4
        blk._block_region_pos = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        blk._block_struct_size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        
        blk._dir_region_pos = struct.unpack_from('I',btarr,offset)[0]
        offset += 4

        return blk


class Dir(object):
    def __init__(self, name="/", inode=0):
        self._name = name
        self._inode = inode
        self._list = []

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
        d = Dir(name, inode)
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
    premcode = ""
    owner = ""
    create_time = ""
    access_time = ""
    modify_time = ""
    file_size = ""
    direct_block = ""
    primary_index = ""

    def __init__(self,owner):  
        create_time = time.time()
        self.premcode = 1      # 1User 0other
        self.owner = 1         # 1Owner  0other
        self.create_time = create_time
        self.access_time = create_time
        self.modify_time = create_time
        self.file_size = 0
        self.direct_block = -1
        self.primary_index = -1

    def encode_into(self,btarr,offset=0):
        struct.pack_into('I',btarr,offset,self.premcode)
        offset += 4
        struct.pack_into('I',btarr,offset,self.owner)
        offset += 4
        struct.pack_into('f',btarr,offset,self.creat_time)
        offset += 4
        struct.pack_into('f',btarr,offset,self.access_time)
        offset += 4
        struct.pack_into('f',btarr,offset,self.modify_time)
        offset += 4
        struct.pack_into('I',btarr,offset,self.file_size)
        offset += 4
        struct.pack_into('I',btarr,offset,self.direct_block)
        offset += 4
        struct.pack_into('I',btarr,offset,self.primary_index)
        offset += 4
        return offset
        
    def decode_from(self,btarr,offset=0):
        self.premcode = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        self.owner = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        self.creat_time = struct.unpack_from('f',btarr,offset)[0]
        offset += 4
        self.access_time = struct.unpack_from('f',btarr,offset)[0]
        offset += 4
        self.modify_time = struct.unpack_from('f',btarr,offset)[0]
        offset += 4
        self.file_size = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        self.direct_block = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        self.primary_index = struct.unpack_from('I',btarr,offset)[0]
        offset += 4
        return offset
     

class Block(object):
    def __init__(self, size=1024):
        self._bytes = bytearray(size)
        self._size = size

    def encode_into(self,btarr,offset=0):
        struct.pack_into(str(self._size)+'s',btarr,offset,self._bytes)

    @classmethod
    def decode_from(cls,btarr,offset=0):
        b = Block()
        b._bytes = struct.unpack_from(str(b._size)+'s',btarr,offset)[0]
        return b

env = {}
env['user'] = "guest"
env['path'] = "/"

class FileSystem(object):
    def __init__(self):
        if os.path.exists('diskfile'):
            with open('diskfile', 'rb') as df:
                self._buffer = bytearray(df.read())
            self._super_block = Superblock.decode_from(self._buffer)

            self._dirs = []
            offset = self._super_block._dir_region_pos
            
            # 循环读目录项
            self._inodes = []
            offset = self._super_block._inode_region_pos

            self._blocks = []
            offset = self._super_block._block_region_pos
            
        else:
            self._buffer = bytearray(100 * 1024 * 1024)
            self._super_block = Superblock()
            self._super_block.encode_into(self._buffer)
            self._dirs, self._inodes, self._blocks = [], [], []
            # 创建根目录

            # 创建用户记录表


            self.save()

        self.openings = {}

    def save(self):
        with open('diskfile', 'wb') as df:
            df.write(self._buffer)

    def add_user(self):
        pass

    def create_file(self):
        pass

    def delete_file(self):
        pass
    
    def open_file(self):
        pass

    def close_file(self):
        pass

    def test_perm(self):
        pass

    def get_uid(self):
        pass

    def login(self):
        pass

    def logout(self):
        env['user'] = 'guest'

    def read_file(self):
        pass

    def write_file(self):
        pass

    def copy_file(self):
        pass

    def change_dir(self):
        pass

    def list_dir(self):
        pass

fsys = FileSystem()

func = {}
func['exit'] = exit
func['echo'] = print
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
        cmd = input().split(' ')
        if cmd[0] == '':
            continue
        if not cmd[0] in func.keys():
            print("Unknown command: {}".format(cmd[0]))
            continue
        if len(cmd) > 1:
            func[cmd[0]](*cmd[1:])
        else:
            func[cmd[0]]()

if __name__ == "__main__":
    main()
