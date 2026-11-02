import os
import random
import requests

# --- حل مشكلة PIL.Image.ANTIALIAS مع الإصدارات الحديثة ---
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, ColorClip
import cloudinary
import cloudinary.uploader

# --- 1. إعدادات البيئة والمفاتيح ---
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
BUFFER_ACCESS_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
# تحويل سلسلة قنوات بافر إلى قائمة
raw_profiles = os.environ.get("BUFFER_PROFILE_IDS")
BUFFER_PROFILE_IDS = raw_profiles.split(",") if raw_profiles else []

# إعدادات Cloudinary
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# --- 2. اختيار الفكرة محلياً ---
def generate_hook():
    print("[1] جاري اختيار فكرة الفيديو...")
    hooks = [
        "8 ÷ 2(2 + 2) = ?\nCan you solve this?",
        "Which way does Gear 7 spin?\nThink carefully!",
        "Can a falling cat always land on its feet?\nPhysics says yes.",
        "99% of people fail this math puzzle!",
        "What happens if you fall into a black hole?"
    ]
    hook_text = random.choice(hooks)
    print(f"الفكرة: {hook_text}")
    return hook_text

# --- 3. سحب مقطع محاكاة من Pexels API ---
def download_video(output_filename="temp_sim.mp4"):
    print("[2] جاري البحث عن مقطع محاكاة في Pexels...")
    queries = ["abstract background", "satisfying motion", "loop background", "blue motion", "digital tunnel"]
    query = random.choice(queries)
    
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"
    headers = {"Authorization": PEXELS_API_KEY}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Pexels API Error: {response.text}")
        
    data = response.json()
    if not data.get('videos'):
        raise Exception("لم يتم العثور على فيديوهات في Pexels.")
        
    random_video = random.choice(data['videos'])
    hd_file = max(random_video['video_files'], key=lambda x: x['width'])
    video_link = hd_file['link']
    
    print("[3] جاري تحميل الفيديو المصدري...")
    vid_data = requests.get(video_link).content
    with open(output_filename, 'wb') as f:
        f.write(vid_data)
    return output_filename

# --- 4. مونتاج الفيديو النهائي عبر MoviePy (يدعم غياب الملفات الخارجية) ---
def create_short(video_path, hook_text, image_path="assets/einstein.jpg", audio_path="assets/phonk_track.mp3", output_path="final_short.mp4"):
    print("[4] جاري دمج ومونتاج الفيديو...")
    CANVAS_W, CANVAS_H = 1080, 1920
    
    top_clip = VideoFileClip(video_path).resize(width=CANVAS_W)
    duration = top_clip.duration
    
    # إذا كانت صورة أينشتاين موجودة سيستخدمها، وإذا لم تكن موجودة سينشئ خلفية داكنة احترافية تلقائياً
    if os.path.exists(image_path):
        bottom_clip = (ImageClip(image_path)
                       .resize(width=CANVAS_W)
                       .set_duration(duration)
                       .set_position(("center", "bottom")))
        top_clip = top_clip.set_position(("center", "top"))
        base_video = CompositeVideoClip([bottom_clip, top_clip], size=(CANVAS_W, CANVAS_H))
    else:
        top_clip = top_clip.resize(height=CANVAS_H).set_position(("center", "center"))
        bg_clip = ColorClip(size=(CANVAS_W, CANVAS_H), color=(15, 15, 25)).set_duration(duration)
        base_video = CompositeVideoClip([bg_clip, top_clip], size=(CANVAS_W, CANVAS_H))
    
    # إضافة النص الجذاب في الأعلى
    txt_clip = (TextClip(hook_text, fontsize=52, color="white", font="DejaVu-Sans-Bold", 
                         stroke_color="black", stroke_width=4, method="caption", 
                         align="center", size=(CANVAS_W - 120, None))
                .set_duration(duration)
                .set_position(("center", 150)))
    
    final_video = CompositeVideoClip([base_video, txt_clip], size=(CANVAS_W, CANVAS_H))
    
    # إضافة الصوت إذا كان موجوداً
    if os.path.exists(audio_path):
        audio_clip = AudioFileClip(audio_path).subclip(0, duration)
        final_video = final_video.set_audio(audio_clip)
        
    final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", threads=2, preset="ultrafast")
    
    top_clip.close()
    final_video.close()
    return output_path

# --- 5. رفع الفيديو لـ Cloudinary للحصول على رابط عام ---
def upload_to_cloud(file_path):
    print("[5] جاري رفع الفيديو لـ Cloudinary للحصول على رابط...")
    response = cloudinary.uploader.upload_large(file_path, resource_type="video")
    return response['secure_url']

# --- 6. النشر التلقائي عبر Buffer API ---
def publish_to_buffer(video_url, hook_text):
    print("[6] جاري إرسال الفيديو لـ Buffer للجدولة...")
    url = "https://api.bufferapp.com/1/updates/create.json"
    
    text_content = f"{hook_text}\n\n#shorts #physics #math #satisfying #geometry #sigma"
    
    data = {
        "access_token": BUFFER_ACCESS_TOKEN,
        "text": text_content,
        "media[video]": video_url
    }
    
    for idx, profile_id in enumerate(BUFFER_PROFILE_IDS):
        data[f"profile_ids[{idx}]"] = profile_id.strip()
        
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("[نجاح] تم إرسال الفيديو لـ Buffer بنجاح لكل المنصات!")
    else:
        print(f"[خطأ Buffer]: {response.text}")

# --- دورة التشغيل الرئيسية ---
if __name__ == "__main__":
    try:
        hook = generate_hook()
        source_vid = download_video()
        final_vid = create_short(video_path=source_vid, hook_text=hook)
        public_video_url = upload_to_cloud(final_vid)
        publish_to_buffer(public_video_url, hook)
    except Exception as e:
        print(f"حدث خطأ أثناء التنفيذ: {e}")
