import os
import stat
import shutil
import boto3
import datetime
import logging
import moviepy
import subprocess
import imageio
#from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

print('Loading function')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

image_path = "/tmp/images"
video_path = "/tmp/video"
video_name = "timelapse.mp4"

# ffmpeg is stored with this script.
# When executing ffmpeg, execute permission is requierd.
# But Lambda source directory do not have permission to change it.
# So move ffmpeg binary to `/tmp` and add permission.
path1 = os.path.dirname(os.path.abspath('ffmpeg'))
print(path1)
ffmpeg_bin = "/tmp/ffmpeg"
shutil.copyfile('/opt/bin/ffmpeg', ffmpeg_bin)
os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_bin
os.chmod(ffmpeg_bin, os.stat(ffmpeg_bin).st_mode | stat.S_IEXEC)

print("OK 1")
from moviepy.config import change_settings
change_settings({"FFMPEG_BINARY": "/tmp/ffmpeg"})
from moviepy.editor import *
#from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

print("OK 2")
s3 = boto3.client('s3')
print("OK 3")
image_bucket = "smart-garden-images"
video_bucket = "smart-garden-generated-timelapse"

print("OK 4")
def prepare_path(target):
  print("prepare path "+target)
  if os.path.exists(target):
    logger.info("{0} exists".format(target))
    shutil.rmtree(target)
  print("mkdir")
  os.mkdir(target)

def copy_object(bucket, source, dest):
  #print("copy object "+dest)
  #print(bucket)
  #print(source)
  name = source.split('/')[-1]
  # print("name "+name)
  local_file = "{0}/{1}".format(dest, name)
  #print(local_file)
  logger.debug("{0} to {1}".format(source, local_file))
  #print("download_file")
  s3.download_file(bucket, source, local_file)
  #print("here")
  if os.path.exists(local_file):
      b = open(local_file,"r")
  return local_file

def create_video(images, video_file):
  print("create video")
  images.sort()
  logger.info("create video from {0} images.".format(len(images)))
  #clip = os.system(ffmpeg_bin+" -i /tmp/IMG%03d.jpg /tmp/video/timelapse.mp4")
  ffmpega="/opt/bin/ffmpeg"
  #command = ffmpega #+" -i /tmp/IMG%03d.jpg /tmp/video/timelapse.mp4"
  imgFilenames = 'IMG%03d.jpg'
  video_file="/tmp/video/timelapse.mp4"
  #ffmpeg -r 6 -pattern_type glob -i '*.JPG' -q:v 10 the-timelapse-video.mov
  #command = ['/opt/bin/ffmpeg','-y', '-i', 'IMG%03d.jpg', '/tmp/video/timelapse.mp4']
  #print(subprocess.check_output([command], stderr=subprocess.STDOUT))
  clip = ImageSequenceClip(images, fps=1)
  clip.write_videofile(video_file)
  ImageSequenceClip(images, fps=1)
  clip.write_videofile(video_file)
  print("clip")
  print(clip)
  logger.info("video: {0}".format(video_file))

def move_video(video_file, bucket, dest_key):
  print("video_file "+video_file)
  print(bucket)
  print(dest_key)

  video = open(video_file,"r")

  s3.put_object(
    Bucket=bucket,
    ACL='public-read',
    Body=video,
    Key=dest_key,
    ContentType="video/mp4"
  )
  logger.info("video moved to {0}/{1}".format(bucket, dest_key))

def lambda_handler(event, context):
  print("hand 1")
  tdatetime = datetime.datetime.now()
  prefix = "raw-pics/00000000be9a0795" #tdatetime.strftime('%Y/%m/%d/')
  result = s3.list_objects_v2(
        Bucket=image_bucket,
        Prefix=prefix
    )
  #print(result)
  print("hand 2 ")

  images = []
  if 'Contents' in result:
    #print("Image path "+image_path)
    prepare_path(image_path)
    for item in result['Contents']:
      if "jpg" in item['Key']:
        #print("item "+item['Key'])
        images.append(copy_object(image_bucket, item['Key'], image_path))
  else:
    return

  if len(images) > 0:
    prepare_path(video_path)
    video_file = "{0}/{1}".format(video_path, video_name)
    create_video(images, video_file)
    prefix1=tdatetime.strftime('%Y/%m/%d/')
    ymd = prefix1.split('/')
    video_key = "{0}/{1}/{2}.mp4".format(ymd[0], ymd[1],"".join(ymd))
    print("Video Key "+ video_key)
    move_video(video_file, video_bucket, video_key)
  else:
    return
