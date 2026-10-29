"""Locate image destinations and replace only bound screenshot occurrences."""
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path
from urllib.parse import unquote, quote


def digest(data):
    return hashlib.sha256(data).hexdigest()


def image_refs(text):
    # Mask code without changing Unicode character offsets.
    masked = re.sub(r'(?ms)^([ \t]*)(`{3,}|~{3,})[^\n]*\n.*?^\1\2[^\n]*(?:\n|$)',lambda m:' '*len(m[0]),text)
    masked = re.sub(r'(`+)([^`]|(?!\1)`)*?\1',lambda m:' '*len(m[0]),masked)
    refs=[]
    for m in re.finditer(r'!\[\[([^\]\n|]+)(?:\|[^\]\n]*)?\]\]',masked):
        refs.append({'start':m.start(1),'end':m.end(1),'original':text[m.start(1):m.end(1)],'syntax':'wiki'})
    for m in re.finditer(r'!\[(?:\\.|[^\]\\])*\]\(\s*',masked):
        start=m.end()
        if start>=len(text):continue
        if text[start]=='<':
            start+=1;end=text.find('>',start)
            if end<0:continue
        else:
            end=start;depth=0
            while end<len(text):
                c=text[end]
                if c=='\\':end+=2;continue
                if c=='(':depth+=1
                elif c==')':
                    if depth==0:break
                    depth-=1
                if c.isspace() and depth==0:break
                end+=1
        if end>start:refs.append({'start':start,'end':end,'original':text[start:end],'syntax':'markdown'})
    return sorted(refs,key=lambda r:r['start'])


def scan(article, vault=None):
    path=Path(article).resolve(strict=True);text=path.read_bytes().decode('utf-8')
    vault=Path(vault).resolve(strict=True) if vault else None
    images=[]
    for ref in image_refs(text):
        raw=unquote(re.sub(r'\\([() ])',r'\1',ref['original']))
        candidates=[]
        if not re.match(r'^[a-z]+://',raw):
            for candidate in [path.parent/raw]+([vault/raw] if vault else []):
                if candidate.is_file() and candidate.resolve() not in candidates:candidates.append(candidate.resolve())
            if not candidates and vault:
                candidates=[p.resolve() for p in vault.rglob(Path(raw).name) if p.is_file() and p.as_posix().endswith(raw)]
        images.append({'path':str(candidates[0]) if len(candidates)==1 else raw,'kind':'unknown','reason':'待查看图片并确认来源' if len(candidates)==1 else '路径缺失或存在多个候选，请先解析','context':text[max(0,ref['start']-250):min(len(text),ref['end']+250)],'references':[ref]})
    return {'title':path.stem,'article_path':str(path),'article_hash':digest(path.read_bytes()),'vault':str(vault) if vault else None,'images':images}


def bind_article(spec, slides, folder):
    if not spec.get('article_path'):return
    path=Path(spec['article_path']).resolve(strict=True)
    if path.suffix.lower() not in ('.md','.markdown'):raise ValueError('回填当前支持本地 Markdown / Obsidian 文章')
    data=path.read_bytes();text=data.decode('utf-8')
    if spec.get('article_hash')!=digest(data):raise ValueError('文章已变化，请重新扫描图片引用')
    possible={(r['start'],r['end'],r['original'],r['syntax']) for r in image_refs(text)}
    refs=[]
    for slide in slides:
        if not slide.get('references'):raise ValueError(f"截图 {slide['id']} 未绑定文章引用，不能整组回填")
        for r in slide['references']:
            if (r['start'],r['end'],r['original'],r['syntax']) not in possible:raise ValueError('引用不对应原文中的图片位置')
            refs.append({**r,'id':slide['id']})
    refs.sort(key=lambda r:r['start'])
    if any(a['end']>b['start'] for a,b in zip(refs,refs[1:])):raise ValueError('图片引用位置重叠')
    state={'path':str(path),'vault':spec.get('vault'),'original':base64.b64encode(data).decode(),'last_hash':digest(data),'refs':refs,'ids':[s['id'] for s in slides]}
    (folder/'article-binding.json').write_text(json.dumps(state,ensure_ascii=False))


def locate_bound_refs(state, text):
    """Relocate known image destinations without trusting stale character offsets."""
    current=image_refs(text);by_original={}
    for ref in current:by_original.setdefault(ref['original'],[]).append(ref)
    bound_by_original={}
    for ref in state['refs']:bound_by_original.setdefault(ref['original'],[]).append(ref)
    located=[];missing=[]
    for original,bound in bound_by_original.items():
        candidates=by_original.get(original,[])
        if len(candidates)>len(bound):
            raise ValueError(f'文章中出现了额外的同名截图引用，无法确认回填目标：{original}')
        ids={ref['id'] for ref in bound}
        if 0<len(candidates)<len(bound) and len(ids)>1:
            raise ValueError(f'同名截图被部分删除，无法确认剩余引用属于哪张成图：{original}')
        for old,live in zip(bound,candidates):located.append({**live,'id':old['id']})
        missing.extend(bound[len(candidates):])
    return sorted(located,key=lambda r:r['start']),missing


def _destination(path, state, asset):
    if state.get('vault'):
        return asset.relative_to(Path(state['vault']).resolve()).as_posix()
    return asset.relative_to(path.parent.resolve()).as_posix()


def reusable_return_files(state, path, refs):
    """Return existing generated files when every active slide has one safe target."""
    root=(path.parent/'screenshot-assets').resolve();base=Path(state['vault']).resolve() if state.get('vault') else path.parent
    files={}
    for item_id in dict.fromkeys(ref['id'] for ref in refs):
        group=[ref for ref in refs if ref['id']==item_id]
        originals={ref['original'] for ref in group}
        if len(originals)!=1:return None
        raw=unquote(next(iter(originals)))
        if re.match(r'^[a-z]+://',raw) or Path(raw).is_absolute():return None
        candidate=(base/raw).resolve()
        if not candidate.is_relative_to(root) or candidate.name!=f'{item_id}-annotated.png' or not candidate.is_file():return None
        files[item_id]=candidate
    if len({file.parent for file in files.values()})!=1:return None
    return files


def refresh_binding(folder):
    """Rebind a saved project to the article's current surviving screenshot refs."""
    folder=Path(folder);binding=folder/'article-binding.json';project_file=folder/'project.json'
    if not binding.exists():raise ValueError('尚未绑定原文章，请先提供完整文章文件')
    state=json.loads(binding.read_text());project=json.loads(project_file.read_text())
    path=Path(state['path']).resolve();before=path.read_bytes();located,missing=locate_bound_refs(state,before.decode('utf-8'))
    active={ref['id'] for ref in located}
    if not active:raise ValueError('文章中已没有任何已绑定截图，未修改项目')
    slides=[]
    for slide in project['slides']:
        if slide['id'] not in active:continue
        slide={**slide,'references':[{k:v for k,v in ref.items() if k!='id'} for ref in located if ref['id']==slide['id']]}
        slides.append(slide)
    known={slide['id'] for slide in slides}
    if known!=active:raise ValueError('项目缺少文章仍在使用的截图，未修改项目')
    project['slides']=slides;state['ids']=[slide['id'] for slide in slides];state['refs']=located
    state['original']=base64.b64encode(before).decode();state['last_hash']=digest(before)
    project_tmp=project_file.with_suffix('.rebind.tmp');binding_tmp=binding.with_suffix('.rebind.tmp')
    project_tmp.write_text(json.dumps(project,ensure_ascii=False));binding_tmp.write_text(json.dumps(state,ensure_ascii=False))
    os.replace(project_tmp,project_file);os.replace(binding_tmp,binding)
    removed=[i for i in dict.fromkeys(ref['id'] for ref in missing) if i not in active]
    return {'slides':len(slides),'references':len(located),'removed_ids':removed,'article':str(path)}


def return_article(folder, images):
    folder=Path(folder);binding=folder/'article-binding.json'
    if not binding.exists():raise ValueError('尚未绑定原文章，请先提供完整文章文件')
    state=json.loads(binding.read_text());path=Path(state['path']).resolve();before=path.read_bytes()
    refs,missing=locate_bound_refs(state,before.decode('utf-8'))
    active_ids=list(dict.fromkeys(ref['id'] for ref in refs))
    if not active_ids:raise ValueError('文章中已没有任何已绑定截图，未修改文章')
    supplied={}
    for item in images:
        item_id=item.get('id')
        if item_id in supplied:raise ValueError('提交的截图 ID 重复')
        supplied[item_id]=item
    absent=[item_id for item_id in active_ids if item_id not in supplied]
    if absent:raise ValueError('缺少文章仍在使用的截图：'+', '.join(absent))
    pngs={}
    for item_id in active_ids:
        item=supplied[item_id]
        data=base64.b64decode(item['png'].split(',',1)[1],validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('导入图片不是 PNG')
        pngs[item_id]=data
    stamp=f'{time.strftime("%Y%m%d-%H%M%S")}-{secrets.token_hex(3)}'
    reuse=reusable_return_files(state,path,refs);mode='overwrite' if reuse else 'new-batch';image_backup=None
    if reuse:
        files=reuse;assets=next(iter(files.values())).parent
    else:
        assets=path.parent/'screenshot-assets'/stamp;assets.mkdir(parents=True,exist_ok=False)
        files={item_id:assets/f"{item_id}-annotated.png" for item_id in active_ids}
    destinations={item_id:_destination(path,state,file) for item_id,file in files.items()}
    updated=before.decode('utf-8')
    rendered={}
    for ref in refs:
        destination=destinations[ref['id']]
        if ref['syntax']=='markdown':destination=quote(destination,safe='/.-_')
        rendered[ref['id']]=destination
    for ref in reversed(refs):
        destination=rendered[ref['id']]
        updated=updated[:ref['start']]+destination+updated[ref['end']:]
    after=updated.encode('utf-8')
    new_refs=[];after_refs=image_refs(updated)
    for item_id in active_ids:
        matches=[ref for ref in after_refs if ref['original']==rendered[item_id]]
        expected=sum(ref['id']==item_id for ref in refs)
        if len(matches)!=expected:raise ValueError('成图写入后无法重新定位，未修改文章')
        new_refs.extend({**ref,'id':item_id} for ref in matches)
    # Original bytes (including BOM and CRLF) are preserved outside destinations.
    backups=folder/'article-backups';backups.mkdir(exist_ok=True)
    backup=backups/f'{stamp}-{path.name}';backup.write_bytes(before)
    if path.read_bytes()!=before:raise ValueError('检测到文章同时被修改，已停止替换；成图与备份已保留')
    if reuse:
        image_backup=folder/'returned-image-backups'/stamp;image_backup.mkdir(parents=True,exist_ok=False)
        for item_id,file in files.items():shutil.copy2(file,image_backup/file.name)
    for item_id,file in files.items():
        tmp=file.with_name(f'.{file.name}.{secrets.token_hex(4)}.tmp')
        try:
            tmp.write_bytes(pngs[item_id]);os.replace(tmp,file)
        finally:
            if tmp.exists():tmp.unlink()
    if after!=before:
        tmp=path.with_name(f'.{path.name}.{secrets.token_hex(4)}.tmp')
        try:
            tmp.write_bytes(after);shutil.copymode(path,tmp);os.replace(tmp,path)
        finally:
            if tmp.exists():tmp.unlink()
    state['last_hash']=digest(after);state['original']=base64.b64encode(after).decode()
    state['refs']=sorted(new_refs,key=lambda r:r['start']);state['ids']=active_ids
    tmpbinding=binding.with_suffix('.tmp');tmpbinding.write_text(json.dumps(state,ensure_ascii=False));os.replace(tmpbinding,binding)
    removed=[i for i in dict.fromkeys(ref['id'] for ref in missing) if i not in active_ids]
    result={'count':len(refs),'skipped':len(missing),'removed_ids':removed,'mode':mode,'article':str(path),'backup':str(backup),'assets':str(assets),'image_backup':str(image_backup) if image_backup else None}
    (folder/'last-import.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result
