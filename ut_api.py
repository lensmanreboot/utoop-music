import subprocess
import json

def search_youtube(query):
    """
    Search YouTube via yt-dlp.
    Returns a list of dictionaries with track information.
    """
    print(f"DEBUG: Starting yt-dlp search for: {query}")
    
    # ytsearch10 requests 10 results
    cmd = [
        "yt-dlp",
        "--print-json",
        "--flat-playlist",
        f"ytsearch10:{query}"
    ]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode != 0:
            print(f"DEBUG: yt-dlp search failed: {stderr}")
            return []
            
        results = []
        for line in stdout.splitlines():
            try:
                item = json.loads(line)
                results.append({
                    "title": item.get("title", "Unknown Title"),
                    "videoId": item.get("id"),
                    "length": item.get("duration", 0),
                    "author": item.get("uploader", "Unknown Author")
                })
            except json.JSONDecodeError:
                continue
                
        print(f"DEBUG: Found {len(results)} results via yt-dlp")
        return results
        
    except Exception as e:
        print(f"DEBUG: yt-dlp execution failed: {type(e).__name__}: {e}")
        return []

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Nokia N900"
    print(f"Searching for: {q}...")
    res = search_youtube(q)
    for i, r in enumerate(res):
        print(f"{i+1}. {r['title']} [{r['length']}s]")
