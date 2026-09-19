"""数据源模块。每个源暴露 fetch(today) -> dict，失败时抛出 FetchError 由主流程降级。"""
