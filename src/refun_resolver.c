// refun_resolver.c - 依赖解析实现
// 拓扑排序和循环依赖检测

#include <string.h>
#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "py/objlist.h"
#include "py/objdict.h"
#include "refun_resolver.h"
#include "refun_version.h"

//=============================================================================
// 拓扑排序实现 (Kahn 算法)
//=============================================================================

// topological_sort(dep_graph) -> list
// 输入: dict of {pkg_name: {dep_name: constraint, ...}, ...}
// 输出: 按加载顺序排列的包名列表
mp_obj_t refun_topological_sort(mp_obj_t dep_graph) {
    if (!mp_obj_is_type(dep_graph, &mp_type_dict)) {
        mp_raise_TypeError(MP_ERROR_TEXT("Expected dict for dep_graph"));
    }

    mp_obj_dict_t *graph = MP_OBJ_TO_PTR(dep_graph);
    mp_obj_t result_list = mp_obj_new_list(0, NULL);

    // 构建入度映射表
    mp_obj_t in_degree = mp_obj_new_dict(0);
    mp_obj_t queue = mp_obj_new_list(0, NULL);

    // 初始化所有入度为 0
    mp_map_t *graph_map = &graph->map;
    for (size_t i = 0; i < graph_map->alloc; i++) {
        if (mp_map_slot_is_filled(graph_map, i)) {
            mp_obj_t pkg_name = graph_map->table[i].key;
            mp_obj_dict_store(MP_OBJ_FROM_PTR(in_degree), pkg_name, MP_OBJ_NEW_SMALL_INT(0));
        }
    }

    // 计算所有节点的入度
    for (size_t i = 0; i < graph_map->alloc; i++) {
        if (mp_map_slot_is_filled(graph_map, i)) {
            mp_obj_t pkg_name = graph_map->table[i].key;
            mp_obj_t deps = graph_map->table[i].value;

            if (mp_obj_is_type(deps, &mp_type_dict)) {
                mp_obj_dict_t *deps_dict = MP_OBJ_TO_PTR(deps);
                mp_map_t *deps_map = &deps_dict->map;

                for (size_t j = 0; j < deps_map->alloc; j++) {
                    if (mp_map_slot_is_filled(deps_map, j)) {
                        mp_obj_t dep_name = deps_map->table[j].key;

                        // 增加入度
                        mp_obj_t current = mp_obj_dict_get(MP_OBJ_FROM_PTR(in_degree), dep_name);
                        if (current == MP_OBJ_NULL) {
                            current = MP_OBJ_NEW_SMALL_INT(0);
                        }
                        mp_obj_dict_store(MP_OBJ_FROM_PTR(in_degree),
                                        dep_name,
                                        MP_OBJ_NEW_SMALL_INT(mp_obj_get_int(current) + 1));
                    }
                }
            }
        }
    }

    // 找出所有入度为 0 的节点
    mp_obj_dict_t *in_degree_dict = MP_OBJ_TO_PTR(in_degree);
    mp_map_t *in_degree_map = &in_degree_dict->map;
    for (size_t i = 0; i < in_degree_map->alloc; i++) {
        if (mp_map_slot_is_filled(in_degree_map, i)) {
            if (mp_obj_get_int(in_degree_map->table[i].value) == 0) {
                mp_obj_list_append(queue, in_degree_map->table[i].key);
            }
        }
    }

    // 处理队列
    while (mp_obj_list_len(queue) > 0) {
        mp_obj_t current = mp_obj_list_pop(queue, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_list_append(result_list, current);

        // 获取当前节点的依赖
        mp_obj_t deps = mp_obj_dict_get(dep_graph, current);
        if (deps != MP_OBJ_NULL && mp_obj_is_type(deps, &mp_type_dict)) {
            mp_obj_dict_t *deps_dict = MP_OBJ_TO_PTR(deps);
            mp_map_t *deps_map = &deps_dict->map;

            for (size_t i = 0; i < deps_map->alloc; i++) {
                if (mp_map_slot_is_filled(deps_map, i)) {
                    mp_obj_t dep_name = deps_map->table[i].key;

                    // 减少入度
                    mp_obj_t degree = mp_obj_dict_get(MP_OBJ_FROM_PTR(in_degree), dep_name);
                    if (degree != MP_OBJ_NULL) {
                        int new_degree = mp_obj_get_int(degree) - 1;
                        mp_obj_dict_store(MP_OBJ_FROM_PTR(in_degree),
                                        dep_name,
                                        MP_OBJ_NEW_SMALL_INT(new_degree));

                        if (new_degree == 0) {
                            mp_obj_list_append(queue, dep_name);
                        }
                    }
                }
            }
        }
    }

    // 检查是否所有节点都已处理（无循环依赖）
    size_t result_len = mp_obj_list_len(result_list);
    if (result_len != graph_map->used) {
        mp_raise_ValueError(MP_ERROR_TEXT("Circular dependency detected"));
    }

    return result_list;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_topological_sort_obj, refun_topological_sort);

//=============================================================================
// 循环依赖检测 (DFS)
//=============================================================================

// 辅助函数: DFS 检测环
static bool dfs_detect_cycle(mp_obj_t graph, mp_obj_t node, mp_obj_t visited, mp_obj_t rec_stack, mp_obj_t path) {
    // 标记当前节点为已访问，并加入递归栈
    mp_obj_dict_store(visited, node, mp_const_true);
    mp_obj_dict_store(rec_stack, node, mp_const_true);
    mp_obj_list_append(path, node);

    // 获取依赖项
    mp_obj_t deps = mp_obj_dict_get(graph, node);
    if (deps != MP_OBJ_NULL && mp_obj_is_type(deps, &mp_type_dict)) {
        mp_obj_dict_t *deps_dict = MP_OBJ_TO_PTR(deps);
        mp_map_t *deps_map = &deps_dict->map;

        for (size_t i = 0; i < deps_map->alloc; i++) {
            if (mp_map_slot_is_filled(deps_map, i)) {
                mp_obj_t dep = deps_map->table[i].key;

                // 如果未访问，递归调用
                mp_obj_t is_visited = mp_obj_dict_get(visited, dep);
                if (is_visited == MP_OBJ_NULL || is_visited == mp_const_false) {
                    if (dfs_detect_cycle(graph, dep, visited, rec_stack, path)) {
                        return true;
                    }
                }
                // 如果在递归栈中，检测到循环
                else if (mp_obj_dict_get(rec_stack, dep) == mp_const_true) {
                    mp_obj_list_append(path, dep);
                    return true;
                }
            }
        }
    }

    // 从递归栈中移除
    mp_obj_dict_store(rec_stack, node, mp_const_false);
    return false;
}

// detect_circular_dep(dep_graph) -> path or None
mp_obj_t refun_detect_circular_dep(mp_obj_t dep_graph) {
    if (!mp_obj_is_type(dep_graph, &mp_type_dict)) {
        mp_raise_TypeError(MP_ERROR_TEXT("Expected dict for dep_graph"));
    }

    mp_obj_t visited = mp_obj_new_dict(0);
    mp_obj_t rec_stack = mp_obj_new_dict(0);

    mp_obj_dict_t *graph = MP_OBJ_TO_PTR(dep_graph);
    mp_map_t *graph_map = &graph->map;

    // 初始化访问标记表
    for (size_t i = 0; i < graph_map->alloc; i++) {
        if (mp_map_slot_is_filled(graph_map, i)) {
            mp_obj_t node = graph_map->table[i].key;
            mp_obj_dict_store(visited, node, mp_const_false);
            mp_obj_dict_store(rec_stack, node, mp_const_false);
        }
    }

    // 从每个未访问的节点开始 DFS
    for (size_t i = 0; i < graph_map->alloc; i++) {
        if (mp_map_slot_is_filled(graph_map, i)) {
            mp_obj_t node = graph_map->table[i].key;

            if (mp_obj_dict_get(visited, node) == mp_const_false) {
                mp_obj_t path = mp_obj_new_list(0, NULL);
                if (dfs_detect_cycle(dep_graph, node, visited, rec_stack, path)) {
                    return path;
                }
            }
        }
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_detect_circular_dep_obj, refun_detect_circular_dep);

//=============================================================================
// 版本匹配
//=============================================================================

// match_version(available_versions, constraint) -> version or None
// 查找匹配约束的最佳（最高）版本
mp_obj_t refun_match_version(mp_obj_t available_versions, mp_obj_t constraint) {
    if (!mp_obj_is_type(available_versions, &mp_type_list)) {
        mp_raise_TypeError(MP_ERROR_TEXT("Expected list for available_versions"));
    }
    if (!mp_obj_is_type(constraint, &refun_constraint_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("Expected Constraint object"));
    }

    refun_constraint_obj_t *c = MP_OBJ_TO_PTR(constraint);
    mp_obj_list_t *versions = MP_OBJ_TO_PTR(available_versions);

    refun_version_obj_t *best = NULL;

    // 查找最佳匹配版本
    for (size_t i = 0; i < versions->len; i++) {
        mp_obj_t ver_obj = versions->items[i];

        if (!mp_obj_is_type(ver_obj, &refun_version_type)) {
            continue;
        }

        refun_version_obj_t *ver = MP_OBJ_TO_PTR(ver_obj);

        if (refun_constraint_matches(c, ver)) {
            if (best == NULL || refun_version_compare(ver, best) > 0) {
                best = ver;
            }
        }
    }

    return best ? MP_OBJ_FROM_PTR(best) : mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_match_version_obj, refun_match_version);
