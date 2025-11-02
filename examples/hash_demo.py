"""
Hash路径转换示例

演示reFun如何使用hash寻址存储实现内容去重
"""

import sys
sys.path.insert(0, '../lib')

import refun
import os


def demo_hash_storage():
    """演示hash存储机制"""

    print("=" * 60)
    print("reFun Hash寻址存储机制演示")
    print("=" * 60)

    # 示例1: 相同内容产生相同hash
    print("\n【示例1】相同内容 → 相同hash → 自动去重")
    print("-" * 60)

    content1 = "class Sensor:\n    def read(self): pass"
    content2 = "class Sensor:\n    def read(self): pass"  # 完全相同

    hash1 = refun.compute_string_hash(content1)
    hash2 = refun.compute_string_hash(content2)

    print(f"内容A hash: {hash1}")
    print(f"内容B hash: {hash2}")
    print(f"两者相同: {hash1 == hash2}")

    path1 = refun.get_hash_path(hash1)
    path2 = refun.get_hash_path(hash2)

    print(f"\n存储路径A: storage/objects/{path1}")
    print(f"存储路径B: storage/objects/{path2}")
    print(f"→ 两个包中的相同文件只存储一次！")


    # 示例2: 不同内容产生不同hash
    print("\n\n【示例2】不同内容 → 不同hash → 分别存储")
    print("-" * 60)

    content_v1 = "VERSION = '1.0.0'"
    content_v2 = "VERSION = '1.1.0'"  # 内容不同

    hash_v1 = refun.compute_string_hash(content_v1)
    hash_v2 = refun.compute_string_hash(content_v2)

    print(f"v1.0.0 hash: {hash_v1}")
    print(f"v1.1.0 hash: {hash_v2}")
    print(f"两者不同: {hash_v1 != hash_v2}")

    path_v1 = refun.get_hash_path(hash_v1)
    path_v2 = refun.get_hash_path(hash_v2)

    print(f"\nv1存储路径: storage/objects/{path_v1}")
    print(f"v2存储路径: storage/objects/{path_v2}")
    print(f"→ 升级时只下载变化的文件！")


    # 示例3: 路径分片
    print("\n\n【示例3】Hash分片 - 避免单目录文件过多")
    print("-" * 60)

    # 模拟多个不同文件
    files = [
        "file_a.py",
        "file_b.py",
        "file_c.py",
        "config.json",
        "utils.py"
    ]

    print("文件分布到不同子目录：\n")
    print("storage/objects/")

    dirs_used = set()
    for filename in files:
        hash_val = refun.compute_string_hash(filename)
        path = refun.get_hash_path(hash_val)
        dir_name = path.split('/')[0]
        dirs_used.add(dir_name)
        print(f"├── {dir_name}/")
        print(f"│   └── {path.split('/', 1)[1][:40]}...  ({filename})")

    print(f"\n→ {len(files)}个文件分散到{len(dirs_used)}个子目录")
    print(f"→ 理论上可分散到256个(16²)子目录")


    # 示例4: 实际应用场景
    print("\n\n【示例4】实际应用 - 包安装过程")
    print("-" * 60)

    print("""
package.json 示例:
{
  "name": "sensor_tools",
  "version": "1.0.0",
  "files": {
    "__init__.py": {
      "hash": "a1b2c3d4e5f67890...",
      "sources": [
        "https://pkg.refun.io/objects/a1/b2c3d4e5f67890...",
        "https://mirror.example.com/objects/a1/b2c3d4e5f67890..."
      ]
    },
    "sensor.py": {
      "hash": "e5f6g7h8i9abcdef...",
      "sources": [...]
    }
  }
}

安装流程:
1. 读取 package.json
2. 遍历 files 列表
3. 对每个文件：
   ├─ 计算存储路径: get_hash_path(hash)
   ├─ 检查 storage/objects/{path} 是否存在
   │  ├─ 存在 → 跳过下载（已有相同内容）✓
   │  └─ 不存在 → 从 sources 下载
   └─ 下载后验证 hash 确保完整性

结果: 重复内容自动去重，节省存储空间！
    """)

    print("\n" + "=" * 60)


if __name__ == '__main__':
    demo_hash_storage()
