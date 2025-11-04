// refun_utils.h - reFun 包管理器实用函数
// 提供优化的路径操作和辅助函数

#ifndef REFUN_UTILS_H
#define REFUN_UTILS_H

#include "py/obj.h"
#include "py/runtime.h"

// 路径操作

// 高效连接路径组件
// 输入: 可变数量的路径部分
// 输出: 连接后的路径字符串
mp_obj_t refun_path_join(size_t n_args, const mp_obj_t *args);

// 标准化路径（处理 .. 和 .）
// 输入: 路径字符串
// 输出: 标准化后的路径字符串
mp_obj_t refun_normalize_path(mp_obj_t path_obj);

// 哈希操作（uhashlib 的封装）

// 计算字符串的 SHA256 哈希值
// 输入: 数据字符串
// 输出: 十六进制摘要字符串
mp_obj_t refun_hash_string(mp_obj_t data_obj);

// 供模块注册使用的外部函数对象
extern const mp_obj_fun_builtin_var_t refun_path_join_obj;
extern const mp_obj_fun_builtin_fixed_t refun_normalize_path_obj;
extern const mp_obj_fun_builtin_fixed_t refun_hash_string_obj;

#endif // REFUN_UTILS_H
