// refun_resolver.h - reFun 包管理器的依赖解析
// 提供拓扑排序和循环依赖检测

#ifndef REFUN_RESOLVER_H
#define REFUN_RESOLVER_H

#include "py/obj.h"
#include "py/runtime.h"
#include "refun_version.h"

// 依赖图的包节点结构
typedef struct {
    mp_obj_t name;              // 包名（字符串）
    refun_version_obj_t *version;
    mp_obj_t deps;              // 字典：{name: Constraint}
} pkg_node_t;

// 依赖图结构
typedef struct {
    pkg_node_t **nodes;
    size_t count;
    size_t capacity;
} dep_graph_t;

// 解析器 API 函数

// 拓扑排序 - 返回安装顺序
// 输入：依赖图（字典）
// 输出：加载顺序的包名列表
mp_obj_t refun_topological_sort(mp_obj_t dep_graph);

// 检测循环依赖
// 输入：依赖图（字典）
// 输出：循环路径（列表）或 None
mp_obj_t refun_detect_circular_dep(mp_obj_t dep_graph);

// 从可用版本中匹配版本
// 输入：可用版本列表，约束对象
// 输出：最佳匹配版本或 None
mp_obj_t refun_match_version(mp_obj_t available_versions, mp_obj_t constraint);

// 用于模块注册的外部函数对象
extern const mp_obj_fun_builtin_fixed_t refun_topological_sort_obj;
extern const mp_obj_fun_builtin_fixed_t refun_detect_circular_dep_obj;
extern const mp_obj_fun_builtin_fixed_t refun_match_version_obj;

#endif // REFUN_RESOLVER_H
