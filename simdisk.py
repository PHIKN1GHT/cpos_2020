import os, math
import numpy as np

class Bitmap(object):
    def __init__(self, n):
        num = n/32 if n%32==0 else math.ceil(n/32)
        self.map = np.zeros(int(num),dtype=np.uint32)
        self._next_pos = 0
        self._total = n
        self._used = 0

    def _tran_pos(self, n):
        sector = int(n/32 if n%32 == 0 else math.floor(n/32))
        offset = n - sector * 32
        return sector, offset

    def set(self,pos,value=True):
        sector, offset = self._tran_pos(pos)
        ori_val = self.map[sector]
        if value:
            new_val = self.map[sector] | (1<<offset)
        else:
            new_val = self.map[sector] & (~(1<<offset))
        if not ori_val == new_val:
            self._used += 1 if value else -1
        self.map[sector] = new_val

    def flip(self,pos):
        self.set(pos, not self.get(pos))

    def get(self,pos):
        sector, offset = self._tran_pos(pos)
        return self.map[sector] >> offset & 1

    def next(self):
        if not self._used < self._total:
            return -1
        while self.get(self._next_pos):
            self._next_pos += 1
            if not self._next_pos < self._total:
                self._next_pos -= self._total
        return self._next_pos

class Superblock(object):
    inode_map_size = ''
    inode_map = ''
    inode_region_pos = ''
    inode_struct_size = ''

    block_map_size = ''
    block_map = ''
    block_region_idx = ''
    block_struct_size = ''

    dir_region_pos = ''
    
    def __init__(self,
        inode_num=102400,
        block_num=102400,
        inode_struct_size=32,
        block_struct_size=1024):
        self.inode_map = Bitmap(inode_num)
        self.block_map = Bitmap(block_num)
        pass

class INode(object):
    premcode = ""
    owner = ""
    create_time = ""
    access_time = ""
    modify_time = ""
    file_size = ""
    pass


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

def init():
    if os.path.exists('diskfile'):
        with open('diskfile', 'rb') as df:
            buffer = bytearray(df.read())
    else:
        buffer = bytearray(100 * 1024 * 1024) # 100MB = 100 * 1024 * 1024 B
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
