// refun_utils.c - 工具函数实现
// 优化的路径操作和辅助函数

#include <string.h>
#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "refun_utils.h"

//=============================================================================
// 路径操作
//=============================================================================

// path_join(*parts) - 连接路径组件
// 示例: path_join("/storage", "objects", "ab", "cdef") -> "/storage/objects/ab/cdef"
mp_obj_t refun_path_join(size_t n_args, const mp_obj_t *args) {
    if (n_args == 0) {
        return mp_obj_new_str("", 0);
    }

    // 计算所需的总长度
    size_t total_len = 0;
    for (size_t i = 0; i < n_args; i++) {
        const char *part = mp_obj_str_get_str(args[i]);
        total_len += strlen(part);
        if (i > 0) total_len++; // 分隔符
    }

    // 分配缓冲区
    char *buf = m_new(char, total_len + 1);
    char *p = buf;

    // 连接各部分
    for (size_t i = 0; i < n_args; i++) {
        const char *part = mp_obj_str_get_str(args[i]);
        size_t part_len = strlen(part);

        // 跳过空部分
        if (part_len == 0) continue;

        // 如果不是第一部分且前一个不以 / 结尾，添加分隔符
        if (p > buf && *(p-1) != '/') {
            *p++ = '/';
        }

        // 复制部分，如果不是第一部分则移除开头的 /
        if (i > 0 && *part == '/') {
            part++;
            part_len--;
        }

        memcpy(p, part, part_len);
        p += part_len;
    }

    *p = '\0';

    mp_obj_t result = mp_obj_new_str(buf, p - buf);
    m_del(char, buf, total_len + 1);

    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(refun_path_join_obj, 0, MP_OBJ_FUN_ARGS_MAX, refun_path_join);

// normalize_path(path) - 通过解析 . 和 .. 来规范化路径
// 示例: "/a/b/../c/./d" -> "/a/c/d"
mp_obj_t refun_normalize_path(mp_obj_t path_obj) {
    const char *path = mp_obj_str_get_str(path_obj);
    size_t path_len = strlen(path);

    // 分配缓冲区
    char *work_buf = m_new(char, path_len + 1);
    char *result_buf = m_new(char, path_len + 1);

    // 复制输入到工作缓冲区
    memcpy(work_buf, path, path_len + 1);

    // 用于存储组件起始位置和长度的栈
    typedef struct {
        const char *start;
        size_t len;
    } component_t;

    component_t stack[64]; // 最大深度 64
    int stack_top = -1;

    bool is_absolute = (work_buf[0] == '/');
    char *p = work_buf;

    // 跳过开头的 /
    if (is_absolute) p++;

    // 处理路径组件
    while (*p) {
        // 查找下一个组件
        char *start = p;
        while (*p && *p != '/') p++;

        size_t len = p - start;

        if (len == 0 || (len == 1 && start[0] == '.')) {
            // 跳过空组件或 "."
        } else if (len == 2 && start[0] == '.' && start[1] == '.') {
            // ".." - 如果栈不为空则弹出
            if (stack_top >= 0) {
                stack_top--;
            }
        } else {
            // 常规组件 - 压入栈
            if (stack_top < 63) {
                stack_top++;
                stack[stack_top].start = start;
                stack[stack_top].len = len;
            }
        }

        // 跳过分隔符
        if (*p == '/') {
            p++;
        }
    }

    // 构建结果
    char *out = result_buf;
    if (is_absolute) {
        *out++ = '/';
    }

    // 从栈复制组件
    for (int i = 0; i <= stack_top; i++) {
        if (i > 0) {
            *out++ = '/';
        }
        memcpy(out, stack[i].start, stack[i].len);
        out += stack[i].len;
    }

    *out = '\0';

    // 处理空结果
    if (out == result_buf || (is_absolute && out == result_buf + 1)) {
        if (is_absolute) {
            strcpy(result_buf, "/");
        } else {
            strcpy(result_buf, ".");
        }
    }

    mp_obj_t result = mp_obj_new_str(result_buf, strlen(result_buf));

    // 清理
    m_del(char, work_buf, path_len + 1);
    m_del(char, result_buf, path_len + 1);

    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_normalize_path_obj, refun_normalize_path);

//=============================================================================
// Hash操作（uhashlib 包装器）
//=============================================================================

// hash_string(data) - 计算字符串的 SHA256 Hash值
// 这是对 uhashlib.sha256() 的便捷包装
mp_obj_t refun_hash_string(mp_obj_t data_obj) {
    // 获取 uhashlib 模块
    mp_obj_t uhashlib = mp_import_name(MP_QSTR_uhashlib, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));

    // 获取 sha256 函数
    mp_obj_t sha256_class = mp_load_attr(uhashlib, MP_QSTR_sha256);

    // 创建Hash对象
    mp_obj_t hash_obj = mp_call_function_0(sha256_class);

    // 更新数据
    mp_obj_t update_method = mp_load_attr(hash_obj, MP_QSTR_update);

    // 如果需要，将字符串转换为字节
    mp_obj_t data_bytes;
    if (mp_obj_is_str(data_obj)) {
        size_t len;
        const char *str = mp_obj_str_get_data(data_obj, &len);
        data_bytes = mp_obj_new_bytes((const byte *)str, len);
    } else {
        data_bytes = data_obj;
    }

    mp_call_function_1(update_method, data_bytes);

    // 获取hexdigest
    mp_obj_t hexdigest_method = mp_load_attr(hash_obj, MP_QSTR_hexdigest);
    return mp_call_function_0(hexdigest_method);
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_hash_string_obj, refun_hash_string);
