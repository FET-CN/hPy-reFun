// refun_fetcher.h - reFun 包管理器的文件下载和对象存储
// 提供从多个源获取文件和对象池管理功能

#ifndef REFUN_FETCHER_H
#define REFUN_FETCHER_H

#include "py/obj.h"
#include "py/runtime.h"

// Fetcher 对象结构
typedef struct {
    mp_obj_base_t base;
    mp_obj_t storage_path;  // 对象存储根目录（字符串）
    mp_obj_t cache_path;    // 缓存目录（字符串或 None）
} refun_fetcher_obj_t;

// 类型声明
extern const mp_obj_type_t refun_fetcher_type;

// Fetcher API 函数
mp_obj_t refun_fetcher_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

// Fetcher 方法
mp_obj_t refun_fetcher_fetch(size_t n_args, const mp_obj_t *args);
mp_obj_t refun_fetcher_get_object_path(mp_obj_t self_in, mp_obj_t hash_obj);
mp_obj_t refun_fetcher_has_object(mp_obj_t self_in, mp_obj_t hash_obj);
mp_obj_t refun_fetcher_store_file(mp_obj_t self_in, mp_obj_t src_path_obj, mp_obj_t expected_hash_obj);

#endif // REFUN_FETCHER_H
