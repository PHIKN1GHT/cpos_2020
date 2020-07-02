

class Bitmap(object):
    def check(self, pos):
        pass

    def get_next(self, size)
        pass

class Superblock(object):
    inode_map = ''
    block_map = ''
    inode_region_pos = ''
    inode_struct_size = ''
    block_region_idx = ''
    block_struct_size = ''
    dir_region_pos = ''
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
