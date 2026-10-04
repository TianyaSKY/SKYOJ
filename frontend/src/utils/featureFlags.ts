// 占位：保留与删除前语义一致（两个能力开关均关闭）。
// 详见 commit dd4572858b4aa5278a95f9f8c9c823d07baca4fc 重构。
const parseEnvBool = (value: unknown, defaultValue = false) => {
    if (value === undefined || value === null || value === '') {
        return defaultValue
    }
    const normalized = String(value).trim().toLowerCase()
    return ['1', 'true', 'yes', 'on'].includes(normalized)
}

export const ENABLE_SEMANTIC_SEARCH = parseEnvBool(import.meta.env.VITE_ENABLE_SEMANTIC_SEARCH, false)
export const ENABLE_PLAGIARISM = parseEnvBool(import.meta.env.VITE_ENABLE_PLAGIARISM, false)
