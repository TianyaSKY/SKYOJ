export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
export interface MessageResponse { message: string }
export interface PaginationQuery { page?: number; page_size?: number }
