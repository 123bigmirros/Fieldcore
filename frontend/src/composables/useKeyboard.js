import { ref, onMounted, onBeforeUnmount } from 'vue'

/**
 * 键盘快捷键管理
 */
export function useKeyboard(handlers = {}) {
    const showGrid = ref(false)

    /**
     * 键盘事件处理
     */
    function handleKeydown(e) {
        // Ctrl+D: 调试信息
        if (e.key === 'd' && e.ctrlKey) {
            e.preventDefault()
            handlers.onDebug?.()
        }

        // Ctrl+G: 切换网格
        if (e.key === 'g' && e.ctrlKey) {
            e.preventDefault()
            toggleGrid()
        }

        // 空格键: 指令输入
        if (e.key === ' ' && handlers.onSpace) {
            handlers.onSpace()
        }
    }

    /**
     * 切换网格显示
     */
    function toggleGrid() {
        showGrid.value = !showGrid.value
        console.log(`🔲 网格辅助线: ${showGrid.value ? '开启' : '关闭'}`)
    }

    // 自动注册和清理事件监听
    onMounted(() => {
        window.addEventListener('keydown', handleKeydown)
        window.addEventListener('resize', handlers.onResize || (() => { }))
    })

    onBeforeUnmount(() => {
        window.removeEventListener('keydown', handleKeydown)
        window.removeEventListener('resize', handlers.onResize || (() => { }))
    })

    return {
        showGrid,
        toggleGrid
    }
}


