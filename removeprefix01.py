'''sample_url="https://www.bing.com"
def print_url(url):
    format_url=url.removeprefix("https://")
    print(format_url)
print_url(sample_url)'''
def format_sth(inputA):
    return inputA.removeprefix("www.")
print(format_sth("www.baidu.com"))