import os
import re
import json
from pathlib import Path
import yt_dlp
import time
from typing import List, Dict
from datetime import datetime

class VideoDownloader:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.raw_dir = self.base_dir / 'raw_videos'
        self.progress_file = self.base_dir / 'download_progress.json'
        self.todo_file = self.base_dir / 'todo.txt'
        self.setup_directories()
        self.load_progress()
        self.search_terms = [
            "helicopter firefighting water drop",
            "skycrane helicopter fire",
            "firehawk helicopter wildfire",
            "helicopter bambi bucket fire",
            "aerial firefighting helicopter"
        ]
        
    def search_youtube_videos(self) -> List[Dict]:
        """Search YouTube for helicopter firefighting videos."""
        videos = []
        ydl_opts = {
            'format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
            'match_filter': lambda info: (
                float(info.get('duration', 999)) <= 60 and  # Under 1 minute
                int(info.get('view_count', 0)) > 1000  # Popular videos
            )
        }
        
        for term in self.search_terms:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    results = ydl.extract_info(f"ytsearch20:{term}", download=False)
                    if results and 'entries' in results:
                        for entry in results['entries']:
                            if entry:
                                videos.append({
                                    'url': f"https://youtube.com/watch?v={entry['id']}",
                                    'title': entry['title'],
                                    'duration': entry.get('duration', 0),
                                    'views': entry.get('view_count', 0)
                                })
                time.sleep(2)  # Avoid rate limiting
            except Exception as e:
                print(f"Error searching {term}: {str(e)}")
                continue
        
        return videos

    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        self.raw_dir.mkdir(exist_ok=True)

    def load_progress(self):
        """Load download progress from JSON file."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {'completed': [], 'failed': []}

    def save_progress(self):
        """Save download progress to JSON file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def format_url(self, url):
        """Format URLs correctly for each platform."""
        # Twitter/X URL formatting
        if 'twitter.com' in url or 'x.com' in url:
            # Ensure we have the full tweet ID
            if not re.search(r'/status/\d+', url):
                return None
        return url

    def parse_todo_list(self):
        """Parse the todo.txt file and extract video URLs."""
        videos = []
        with open(self.todo_file, 'r') as f:
            for line in f:
                if line.startswith('- [ ]'):
                    match = re.search(r'https?://[^\s]+', line)
                    if match:
                        url = self.format_url(match.group(0))
                        if not url:
                            continue
                        
                        duration_match = re.search(r'\((\d+):(\d+)\)', line)
                        if duration_match:
                            minutes, seconds = map(int, duration_match.groups())
                            duration = minutes * 60 + seconds
                            if duration <= 60:
                                videos.append({
                                    'url': url,
                                    'duration': duration,
                                    'line': line.strip()
                                })
        return videos

    def get_ydl_opts(self, platform):
        """Get platform-specific yt-dlp options."""
        common_opts = {
            'format': 'mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': str(self.raw_dir / '%(title)s.%(ext)s'),
            'max_filesize': 100000000,  # 100MB max
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'concurrent_fragment_downloads': 8,
            'retries': 3,
            'fragment_retries': 3,
            'file_access_retries': 3,
        }

        if platform == 'instagram':
            common_opts.update({
                'cookiesfile': str(self.base_dir / 'instagram_cookies.txt'),
                'add_header': [
                    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                ]
            })
        elif platform == 'reddit':
            common_opts.update({
                'cookiesfile': str(self.base_dir / 'reddit_cookies.txt')
            })

        return common_opts

    def download_video(self, video):
        """Download a single video using yt-dlp with retries and platform-specific handling."""
        if video['url'] in self.progress['completed']:
            print(f"Skipping already downloaded: {video['line']}")
            return True

        platform = 'instagram' if 'instagram.com' in video['url'] else \
                  'reddit' if 'reddit.com' in video['url'] else \
                  'twitter' if any(x in video['url'] for x in ['twitter.com', 'x.com']) else 'other'

        ydl_opts = self.get_ydl_opts(platform)
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    print(f"Downloading: {video['line']}")
                    ydl.download([video['url']])
                    self.progress['completed'].append(video['url'])
                    self.save_progress()
                    return True
            except Exception as e:
                print(f"Error downloading {video['url']} (attempt {retry_count + 1}/{max_retries}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5)  # Wait 5 seconds before retrying
        
        self.progress['failed'].append(video['url'])
        self.save_progress()
        return False

    def run(self):
        """Main execution method."""
        # First try existing todo list
        videos = self.parse_todo_list()
        print(f"Found {len(videos)} videos in todo list")
        
        # Then search YouTube for more videos
        if len(videos) < 50:
            print("\nSearching YouTube for additional videos...")
            youtube_videos = self.search_youtube_videos()
            print(f"Found {len(youtube_videos)} videos on YouTube")
            
            # Add new videos to todo.txt
            with open(self.todo_file, 'a') as f:
                f.write("\n## YouTube Videos\n")
                for video in youtube_videos:
                    if video['url'] not in [v['url'] for v in videos]:
                        duration_str = f"({int(video['duration'])}s)"
                        line = f"- [ ] {video['url']} - {video['title']} {duration_str}\n"
                        f.write(line)
                        videos.append({
                            'url': video['url'],
                            'duration': video['duration'],
                            'line': line.strip()
                        })
        
        print(f"\nAttempting to download {len(videos)} total videos")
        successful = len(self.progress['completed'])
        failed = len(self.progress['failed'])
        
        for video in videos:
            if video['url'] not in self.progress['completed'] and video['url'] not in self.progress['failed']:
                if self.download_video(video):
                    successful += 1
                else:
                    failed += 1
                print(f"Progress: {successful}/{len(videos)} downloaded, {failed} failed")
        
        print(f"\nDownload complete!")
        print(f"Successfully downloaded: {successful} videos")
        print(f"Failed downloads: {failed} videos")
        
        if failed > 0:
            print("\nFailed URLs:")
            for url in self.progress['failed']:
                print(f"- {url}")

if __name__ == "__main__":
    downloader = VideoDownloader()
    downloader.run()
