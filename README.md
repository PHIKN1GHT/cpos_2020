# cpos_2020
Course Project of Operating System

文件名：diskfile

用户记录->储存于文件系统内
/userinfo文件，json格式，[{user: str, uid:int32}]
默认用户：
- system, uid=0
- guest, uid=1

超级块（4KB+8KB+20B<16KB）
- INode位图(32768个/8位=4096B)
- Block位图(65536个/8位=8192B)
- INode区起始地址 4B
- INode项大小 4B
- 数据区起始地址 4B
- 数据区块大小 4B
- 目录区起始地址 4B
- 填充

目录块 (4096 KB)
- 目录名 32B
- INODE号 4B
- 记录长度 4B
- 记录项 （文件名列表）
- 文件名&Inode号(32B+4B)*n

INODE区（1024KB / 32B = 32768个）
- 权限（只用户和其它）4B（仅使用第一个字节）
- 拥有者 4B
- 创建日期 4B (Unix时间戳)
- 访问日期 4B
- 修改日期 4B
- 文件大小 4B
- 直接块 4B
- 一级索引 4B(=-1则表示无需一级索引)

数据区(BlockSize = 2KB, BlockNum=100 * 1024 / 2=51200个<65536)
最大文件大小=2*1024/4*2*1024 = 1024KB

打开文件列表：
inode_id->set

初始化过程：
1. 创建超级块，指定目录区、INode区与数据区的开始地址
2. 初始化目录区，为系统建立根目录




info -> 
login username -> 改变当前用户身份
adduser username uid-> 创建用户
dir/ls -> 列出目录（文件名，物理地址，保护码，文件大小）
create filename (paddingsize) -> 创建文件（用时间戳生成inode）
delete filename -> 删除文件（检查引用数，文件名索引到inode）
open filename-> 打开文件（增加引用数）
close filename-> 关闭文件（删除引用数）
read filename bytes-> 读出文件内容（要求已打开）
write filename data-> 写到文件（要求已打开）
copy src dst-> 复制文件
cd filename -> 设置工作目录
exit -> 退出
























