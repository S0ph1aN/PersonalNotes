def celebrate_with_code_fireworks():
    """在终端绽放代码烟花"""
    import time
    colors = ['\033[91m', '\033[93m', '\033[94m', '\033[95m', '\033[96m']
    reset = '\033[0m'
    
    for _ in range(10):
        pattern = "✨ " * (10 - _ % 10) + "★ " + "✨ " * (_ % 10)
        color = colors[_ % len(colors)]
        print(f"\r{color}{pattern}{reset}", end='', flush=True)
        time.sleep(0.2)
    
    print("\n感谢使用通义灵码！您的满意就是我最好的能量源 💡")
def main():
    """主函数"""
    celebrate_with_code_fireworks()