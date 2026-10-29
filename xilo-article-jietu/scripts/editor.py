#!/usr/bin/env python3
"""Create and serve an editable screenshot project. Standard library only."""
import argparse, base64, json, mimetypes, os, secrets, shutil, subprocess, sys, threading, time, zipfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from article import bind_article, refresh_binding, return_article, scan

ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = Path(os.environ.get('XILO_ARTICLE_JIETU_CONFIG_DIR') or Path.home()/'.config'/'xilo-article-jietu')
WATERMARK_TYPES = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}

def watermark_path():
    for ext in WATERMARK_TYPES:
        if (CONFIG_DIR/f'watermark{ext}').is_file(): return CONFIG_DIR/f'watermark{ext}'

def default_watermark():
    path = watermark_path()
    if not path: return None
    return f'data:{WATERMARK_TYPES[path.suffix]};base64,'+base64.b64encode(path.read_bytes()).decode()

def set_watermark(source):
    source = Path(source).expanduser().resolve(strict=True)
    ext = source.suffix.lower()
    if ext not in WATERMARK_TYPES or source.stat().st_size > 20*1024*1024:
        raise ValueError('水印需为不超过 20 MB 的 PNG、JPG 或 WebP')
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    old = watermark_path()
    if old: shutil.copy2(old, old.with_name(f'watermark.{time.strftime("%Y%m%d-%H%M%S")}.bak{old.suffix}')); old.unlink()
    shutil.copy2(source, CONFIG_DIR/f'watermark{ext}')
    return CONFIG_DIR/f'watermark{ext}'

def create(manifest, output):
    spec = json.loads(Path(manifest).read_text())
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out/'originals').mkdir()
    slides, excluded = [], []
    for n, item in enumerate(spec['images']):
        if item.get('kind') != 'screenshot':
            excluded.append({'path': item.get('path'), 'kind': item.get('kind','unknown'), 'reason': item.get('reason','来源未确认，不处理')})
            continue
        source = Path(item['path']).resolve(strict=True)
        mime = mimetypes.guess_type(source.name)[0]
        if mime not in ('image/png','image/jpeg','image/webp'):
            raise ValueError(f'仅支持 PNG/JPEG/WebP 截图：{source}')
        shutil.copy2(source, out/'originals'/f'{n+1:03}{source.suffix.lower()}')
        slides.append({'id':f's{n+1:03}', 'name':item.get('name',source.stem), 'source':str(source),
            'references':item.get('references',[]), 'context':item.get('context',''), 'evidence':item.get('evidence',''),
            'image':'data:'+mime+';base64,'+base64.b64encode(source.read_bytes()).decode(),
            'style':{'width':1600,'height':1000,'padding':70,'scale':1,'offsetX':0,'offsetY':0,'radius':24,'shadow':25,'bg':['#087f8c','#b5e8ba'],'bgImage':None, **item.get('style',{})},
            'annotations':item.get('annotations',[]), 'reviewed':False})
    if not slides:
        raise ValueError('没有来源确认的截图；不把未知图片或 AI 图片当作截图')
    project={'version':1,'defaultWatermark':default_watermark(),'title':spec.get('title','文章截图工作室'),'slides':slides,'excluded':excluded}
    bind_article(spec,slides,out)
    (out/'project.json').write_text(json.dumps(project,ensure_ascii=False))
    shutil.copy2(ROOT/'assets/editor.html',out/'index.html')
    return out

def export_files(folder, obj):
    images = obj.get('images', [])
    if not images: raise ValueError('没有可导出的图片')
    decoded = []
    for item in images:
        data = base64.b64decode(item['png'].split(',', 1)[1], validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('PNG 格式不正确')
        decoded.append(data)
    dest = Path(folder)/'exports'/f'{time.strftime("%Y%m%d-%H%M%S")}-{secrets.token_hex(3)}'
    dest.mkdir(parents=True)
    for i, data in enumerate(decoded): (dest/f'{i+1:03}-annotated.png').write_bytes(data)
    (dest/'mapping.json').write_text(json.dumps(obj.get('mapping', []), ensure_ascii=False, indent=2))
    with zipfile.ZipFile(dest/'screenshots.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for file in dest.glob('*.png'): z.write(file, file.name)
        z.write(dest/'mapping.json', 'mapping.json')
    filename = '001-annotated.png' if obj.get('single') else 'screenshots.zip'
    return {'path': str(dest), 'batch': dest.name, 'count': len(decoded),
            'download': f'/exports/{dest.name}/{filename}'}

def exported_path(folder, relative):
    root = (Path(folder)/'exports').resolve()
    candidate = (root/relative).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError('导出路径无效')
    return candidate

def serve(folder, port):
    folder=Path(folder).resolve()
    token=secrets.token_urlsafe(24)
    write_lock=threading.RLock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def reply(self,data,status=200,mime='application/json'):
            self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            path=urlparse(self.path).path
            files={'/':('index.html','text/html; charset=utf-8'),'/project.json':('project.json','application/json')}
            if path=='/session':
                binding=folder/'article-binding.json'
                name=Path(json.loads(binding.read_text())['path']).name if binding.exists() else None
                return self.reply(json.dumps({'token':token,'article':name,'defaultWatermark':default_watermark()},ensure_ascii=False).encode())
            if path.startswith('/exports/'):
                try:
                    file = exported_path(folder, path[len('/exports/'):])
                    if not file.is_file() or file.suffix not in ('.png', '.zip', '.json'): raise ValueError('文件不存在')
                    self.send_response(200)
                    self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{file.name}"')
                    self.send_header('Content-Length', str(file.stat().st_size))
                    self.end_headers()
                    with file.open('rb') as source: shutil.copyfileobj(source, self.wfile)
                    return
                except ValueError: return self.reply(b'Not found', 404)
            if path not in files: return self.reply(b'Not found',404)
            file,mime=files[path]; self.reply((folder/file).read_bytes(),mime=mime)
        def do_POST(self):
            if self.headers.get('X-Editor-Token')!=token: return self.reply(b'Forbidden',403)
            if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{self.server.server_port}'):
                return self.reply(b'Forbidden origin',403)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=200_000_000: raise ValueError('文件超过 200 MB')
                obj=json.loads(self.rfile.read(size))
                if self.path=='/return-article':
                    with write_lock:
                        result=return_article(folder,obj['images'])
                    return self.reply(json.dumps(result,ensure_ascii=False).encode())
                if self.path=='/save':
                    if obj.get('version')!=1 or not obj.get('slides'): raise ValueError('项目格式不正确')
                    # Atomic save, plus one recovery copy of the prior state.
                    tmp=folder/'project.tmp'; tmp.write_text(json.dumps(obj,ensure_ascii=False))
                    shutil.copy2(folder/'project.json',folder/'project.previous.json')
                    os.replace(tmp,folder/'project.json')
                    return self.reply(b'{"ok":true}')
                if self.path=='/open-export':
                    dest=exported_path(folder,obj['batch'])
                    if not dest.is_dir() or dest.parent != folder/'exports': raise ValueError('导出文件夹不存在')
                    command=['open',str(dest)] if sys.platform=='darwin' else ['explorer',str(dest)] if os.name=='nt' else ['xdg-open',str(dest)]
                    subprocess.run(command,check=True,timeout=10,capture_output=True)
                    return self.reply(b'{"ok":true}')
                if self.path=='/export':
                    result=export_files(folder,obj)
                    return self.reply(json.dumps(result,ensure_ascii=False).encode())
                self.reply(b'Not found',404)
            except Exception as exc:
                self.reply(json.dumps({'error':str(exc)},ensure_ascii=False).encode(),400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'http://127.0.0.1:{server.server_port}',flush=True)
    print(f'Project: {folder}',flush=True)
    server.serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('scan'); a.add_argument('--article',required=True); a.add_argument('--vault'); a.add_argument('--output',required=True)
    c=sub.add_parser('create'); c.add_argument('--manifest',required=True); c.add_argument('--output',required=True)
    r=sub.add_parser('rebind'); r.add_argument('--project',required=True)
    w=sub.add_parser('watermark',help='查看或设置默认 IP 水印'); w.add_argument('--set'); w.add_argument('--clear',action='store_true')
    s=sub.add_parser('serve'); s.add_argument('--project',required=True); s.add_argument('--port',type=int,default=0)
    args=p.parse_args()
    if args.command=='scan':
        Path(args.output).write_text(json.dumps(scan(args.article,args.vault),ensure_ascii=False,indent=2))
        print(args.output)
    elif args.command=='create': print(create(args.manifest,args.output))
    elif args.command=='watermark':
        if args.set: print(set_watermark(args.set))
        elif args.clear:
            old=watermark_path()
            if old: old.rename(old.with_name(f'watermark.{time.strftime("%Y%m%d-%H%M%S")}.bak{old.suffix}'))
            print('已移除默认水印' if old else '没有默认水印')
        else: print(watermark_path() or f'未设置默认水印（目录：{CONFIG_DIR}）')
    elif args.command=='rebind': print(json.dumps(refresh_binding(args.project),ensure_ascii=False))
    else: serve(args.project,args.port)
