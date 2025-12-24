import {defineStore} from 'pinia'
import {ref} from 'vue'
import {getSysInfo} from '@/api/sys'

export const useSysStore = defineStore('sys', () => {
    const title = ref('SKYOJ')
    const practice = ref(true)
    const info = ref('')
    const warning = ref(false)

    const fetchSysInfo = async () => {
        try {
            const res = await getSysInfo()
            if (res) {
                if (res.title) {
                    title.value = res.title
                    document.title = res.title
                }
                if (res.practice !== undefined) practice.value = res.practice
                if (res.info) info.value = res.info
                if (res.warning !== undefined) warning.value = res.warning
            }
        } catch (error) {
            console.error('Failed to fetch system info:', error)
        }
    }

    return {title, practice, info, warning, fetchSysInfo}
})
