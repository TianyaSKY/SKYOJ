const parseEnvBool = (value, defaultValue = false) => {
  if (value === undefined || value === null || value === '') {
    return defaultValue
  }
  const normalized = String(value).trim().toLowerCase()
  return ['1', 'true', 'yes', 'on'].includes(normalized)
}

export const ENABLE_SEMANTIC_SEARCH = parseEnvBool(import.meta.env.VITE_ENABLE_SEMANTIC_SEARCH, false)
export const ENABLE_PLAGIARISM = parseEnvBool(import.meta.env.VITE_ENABLE_PLAGIARISM, false)
