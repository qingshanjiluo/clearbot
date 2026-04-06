import os
import time
from login import BBSTurkeyBotLogin
from post import BBSPoster

class SelfThreadCleaner:
    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "https://mbbs.zdjl.site/mk48by049.mbbs.cc")
        self.username = os.getenv("BOT_USERNAME")
        self.password = os.getenv("BOT_PASSWORD")
        # 处理空字符串情况
        keep_str = os.getenv("KEEP_LATEST_COUNT", "10")
        self.keep_latest = int(keep_str) if keep_str else 5

        if not self.username or not self.password:
            raise ValueError("请设置 BOT_USERNAME 和 BOT_PASSWORD")

        self.token = None
        self.user_id = None
        self.session = None
        self.poster = None

    def login(self):
        login_bot = BBSTurkeyBotLogin(self.base_url, self.username, self.password, max_retries=3)
        success, result, session = login_bot.login_with_retry()
        if not success:
            print("❌ 登录失败")
            return False
        self.token = result['data']['token']
        self.user_id = result['data']['id']
        self.session = session
        self.poster = BBSPoster(session, self.base_url)
        print(f"✅ 登录成功，用户ID: {self.user_id}")
        return True

    def get_my_threads(self):
        """获取当前登录用户的所有帖子（按时间倒序）"""
        all_threads = []
        page = 0
        while True:
            threads = self.poster.get_threads(self.token, user_id=self.user_id, page_limit=20, page_offset=page)
            if not threads:
                break
            all_threads.extend(threads)
            if len(threads) < 20:
                break
            page += 1
        # 按创建时间倒序排序（最新的在前）
        all_threads.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return all_threads

    def delete_thread(self, thread_id):
        """删除自己的帖子（使用普通删除接口）"""
        try:
            headers = {'Authorization': self.token}
            url = f"{self.poster.api_base}/bbs/threads/{thread_id}"
            resp = self.session.delete(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                print(f"✅ 删除帖子成功: {thread_id}")
                return True
            else:
                print(f"❌ 删除失败 {thread_id}: HTTP {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ 删除异常 {thread_id}: {e}")
            return False

    def run(self):
        print(f"🧹 开始清理自己的帖子，保留最新 {self.keep_latest} 个")
        if not self.login():
            return

        threads = self.get_my_threads()
        total = len(threads)
        print(f"📊 共获取到 {total} 个帖子")

        if total <= self.keep_latest:
            print("✅ 帖子数量未超过保留数，无需清理")
            return

        to_delete = threads[self.keep_latest:]  # 保留前 N 个最新的，删除其余
        print(f"🗑️ 需要删除 {len(to_delete)} 个帖子")

        for idx, thread in enumerate(to_delete, 1):
            tid = thread['id']
            title = thread.get('title', '无标题')
            print(f"  删除 [{idx}/{len(to_delete)}] {title} (ID: {tid})")
            self.delete_thread(tid)
            time.sleep(1)

        print("✅ 清理完成")

if __name__ == "__main__":
    cleaner = SelfThreadCleaner()
    cleaner.run()
