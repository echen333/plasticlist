import os
import re
import json
import time
import requests
from pathlib import Path
import yt_dlp
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
            "aerial firefighting helicopter",
            "firefighting helicopter water drop",
            "helicopter wildfire response",
            "aerial firefighting operations"
        ]
        self.video_platforms = {
            'vimeo': {
                'base_url': 'https://vimeo.com/search?q=',
                'video_url': 'https://vimeo.com/'
            },
            'dailymotion': {
                'base_url': 'https://www.dailymotion.com/video/',
                'video_url': 'https://www.dailymotion.com/video/'
            }
        }
        
    def search_platform_videos(self) -> List[Dict]:
        """Search multiple platforms for helicopter firefighting videos."""
        videos = []
        ydl_opts = {
            'format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'match_filter': lambda info: (
                float(info.get('duration', 999)) <= 60  # Under 1 minute
            )
        }
        
        for platform, platform_info in self.video_platforms.items():
            print(f"\nSearching {platform} for videos...")
            for term in self.search_terms:
                try:
                    if platform == 'vimeo':
                        search_url = f"{platform_info['base_url']}{term.replace(' ', '+')}"
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            results = ydl.extract_info(search_url, download=False, process=False)
                            if results and 'entries' in results:
                                for entry in results['entries'][:5]:  # Limit to first 5 results per term
                                    if entry:
                                        video_url = f"{platform_info['video_url']}{entry['id']}"
                                        try:
                                            video_info = ydl.extract_info(video_url, download=False)
                                            if video_info and video_info.get('duration', 999) <= 60:
                                                videos.append({
                                                    'url': video_url,
                                                    'title': video_info.get('title', 'Untitled'),
                                                    'duration': video_info.get('duration', 0),
                                                    'views': video_info.get('view_count', 0),
                                                    'platform': platform
                                                })
                                        except Exception as e:
                                            print(f"Error processing video {video_url}: {str(e)}")
                                            continue
                    elif platform == 'dailymotion':
                        # Use Dailymotion API endpoint for search
                        search_url = f"https://api.dailymotion.com/videos?fields=id,title,duration,views_total&search={term.replace(' ', '+')}&limit=5"
                        import requests
                        response = requests.get(search_url)
                        if response.status_code == 200:
                            data = response.json()
                            for video in data.get('list', []):
                                if video.get('duration', 999) <= 60:
                                    video_url = f"{platform_info['video_url']}{video['id']}"
                                    videos.append({
                                        'url': video_url,
                                        'title': video.get('title', 'Untitled'),
                                        'duration': video.get('duration', 0),
                                        'views': video.get('views_total', 0),
                                        'platform': platform
                                    })
                    time.sleep(2)  # Sleep between searches
                except Exception as e:
                    print(f"Error searching {platform} - {term}: {str(e)}")
                    continue
            
            print(f"Found {len(videos)} videos on {platform}")
        
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
        instagram_urls = []
        
        with open(self.todo_file, 'r') as f:
            content = f.readlines()
            
        # First pass: collect all valid URLs
        for line in content:
            if line.startswith('- [ ]'):
                match = re.search(r'https?://[^\s]+', line)
                if match:
                    url = self.format_url(match.group(0))
                    if not url:
                        continue
                    
                    # Skip Instagram URLs
                    if 'instagram.com' in url:
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
        
        # Clean up todo.txt to remove Instagram section
        new_content = []
        in_instagram_section = False
        for line in content:
            if '## Instagram Videos' in line:
                in_instagram_section = True
                continue
            if in_instagram_section and line.strip() and not line.startswith('#'):
                continue
            if line.startswith('##') and '## Instagram Videos' not in line:
                in_instagram_section = False
            if not in_instagram_section:
                new_content.append(line)
        
        # Write back cleaned todo.txt
        with open(self.todo_file, 'w') as f:
            f.writelines(new_content)
        
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
            'concurrent_fragment_downloads': 1,  # Reduced to avoid rate limiting
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 10,
            'sleep_interval': 15,  # Increased sleep between retries
            'max_sleep_interval': 60,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'socket_timeout': 30,
            'extractor_retries': 5,
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
        # First try existing todo list (excluding Instagram)
        videos = self.parse_todo_list()
        print(f"Found {len(videos)} non-Instagram videos in todo list")
        
        # Then search YouTube for more videos
        if len(videos) < 50:
            print("\nSearching additional platforms for videos...")
            platform_videos = self.search_platform_videos()
            total_new = len(platform_videos)
            print(f"\nFound {total_new} total videos across all platforms")
            
            if total_new > 0:
                # Add new videos to todo.txt
                with open(self.todo_file, 'a') as f:
                    for platform in self.video_platforms.keys():
                        platform_specific = [v for v in platform_videos if v['platform'] == platform]
                        if platform_specific:
                            f.write(f"\n## {platform.title()} Videos\n")
                            for video in platform_specific:
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
        
        # Prioritize YouTube videos first
        youtube_videos = [v for v in videos if 'youtube.com' in v['url']]
        other_videos = [v for v in videos if 'youtube.com' not in v['url']]
        videos = youtube_videos + other_videos
        
        for video in videos:
            if video['url'] not in self.progress['completed'] and video['url'] not in self.progress['failed']:
                if self.download_video(video):
                    successful += 1
                else:
                    failed += 1
                print(f"Progress: {successful}/{len(videos)} downloaded, {failed} failed")
                # Stop if we have enough videos
                if successful >= 50:
                    print("\nReached target of 50 videos!")
                    break
        
        print(f"\nDownload complete!")
        print(f"Successfully downloaded: {successful} videos")
        print(f"Failed downloads: {failed} videos")
        
        if failed > 0:
            print("\nFailed URLs:")
            for url in self.progress['failed']:
                print(f"- {url}")
        
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
