import urllib.request, tarfile, io, os, shutil, time, traceback

URL = "https://github.com/zhengr/knowledge-base/archive/refs/heads/main.tar.gz"
DATA = "/data"
TARGET = "/data/kb-self"
INTERVAL = 86400  # 每天一次

def update_once():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 拉取最新知识库...", flush=True)
    data = urllib.request.urlopen(URL, timeout=120).read()
    print(f"  下载 {len(data)} bytes", flush=True)
    tmp = "/data/_kbtmp"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp, exist_ok=True)
    tf = tarfile.open(fileobj=io.BytesIO(data))
    tf.extractall(tmp, filter="data")
    names = tf.getnames()
    top = names[0].split("/")[0]
    src = os.path.join(tmp, top)
    # 覆盖目标
    if os.path.exists(TARGET):
        shutil.rmtree(TARGET)
    os.rename(src, TARGET)
    shutil.rmtree(tmp)
    wiki = os.path.join(TARGET, "wiki")
    cnt = sum(len(files) for _, _, files in os.walk(wiki)) if os.path.isdir(wiki) else 0
    print(f"  更新完成: {TARGET} (wiki 文件 {cnt} 个)", flush=True)

if __name__ == "__main__":
    # 首次立即跑一次，之后每天 UTC 16:30 拉取（等 Actions 16:00 构建 push 完）
    try:
        update_once()
    except Exception as e:
        print("首次更新失败:", e, flush=True)
        traceback.print_exc()
    while True:
        # 计算到下一个 UTC 16:30 的秒数
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc)
        target = now.replace(hour=16, minute=30, second=0, microsecond=0)
        if target <= now:
            target = target + _dt.timedelta(days=1)
        wait = (target - now).total_seconds()
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 下次更新于 UTC 16:30 (等待 {int(wait)}s)", flush=True)
        time.sleep(wait)
        try:
            update_once()
        except Exception as e:
            print("更新失败(重试下次):", e, flush=True)
