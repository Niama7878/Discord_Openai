is_processing = False # 处理事件状态

def processing(status: bool = None):
    # 修改状态
    global is_processing
    if status is not None:  # 只有在传入参数时才修改状态
        is_processing = status
    return is_processing  # 返回当前状态