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

    # create new file
    def __init__(self,owner): 
        now_time = time.time()
        create_time = self.packed(now_time)
        self.premcode = 1                    # 1User 0notUser
        self.owner = self.packed(owner)      # If not packed
        self.create_time = create_time
        self.access_time = create_time
        self.modify_time = create_time
        self.file_size = self.packed(0)
        self.direct_block = self.packed(-1)
        self.primary_index = self.packed(-1)

    def packed(self,obj): 
        return struct.pack("f",obj)

    def unpacked(self,obj): 
        return struct.unpack("f",obj)


class Block(object):
    pass

def logout():
    env['user'] = 'guest'

env = {}
env['user'] = "guest"
env['path'] = "/"

func = {}
func['exit'] = exit
func['echo'] = print
func['logout'] = logout

buffer = b''

class FileSystem(object):
    def __init__(self,buffer=None):
        if buffer:
            self._super_block = Superblock.decode_from(buffer)


fsys = FileSystem()

def init():
    if os.path.exists('diskfile'):
        with open('diskfile', 'rb') as df:
            buffer = bytearray(df.read())
    else:
        buffer = bytearray(100 * 1024 * 1024) # 100MB = 100 * 1024 * 
        with open('diskfile', 'wb') as df:
            df.write(buffer)


def load_superblock():
    superblock = ''

def main():
    init()
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
