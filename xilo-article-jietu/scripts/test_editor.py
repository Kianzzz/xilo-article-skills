"""Regression checks for source preservation and screenshot-only processing."""
import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from editor import create

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.png=self.root/'source.png'
        self.png.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
    def manifest(self, images):
        path=self.root/'input.json';path.write_text(json.dumps({'images':images}));return path
    def test_mixed_sources(self):
        before=hashlib.sha256(self.png.read_bytes()).digest()
        m=self.manifest([{'path':str(self.png),'kind':'screenshot','annotations':[{'type':'text','x':.1,'y':.1,'text':'输入任务'},{'type':'mosaic','x':.2,'y':.2,'w':.3,'h':.2,'blockSize':20}]}, {'path':'nonexistent-ai.png','kind':'ai-generated'}, {'path':'nonexistent-unknown.png','kind':'unknown'}])
        out=create(m,self.root/'project');data=json.loads((out/'project.json').read_text())
        self.assertEqual(len(data['slides']),1);self.assertEqual(len(data['excluded']),2)
        self.assertEqual(data['slides'][0]['annotations'][0]['text'],'输入任务')
        self.assertEqual(data['slides'][0]['annotations'][1],{'type':'mosaic','x':.2,'y':.2,'w':.3,'h':.2,'blockSize':20})
        self.assertEqual(data['slides'][0]['style']['bg'],['#087f8c','#b5e8ba'])
        self.assertEqual(hashlib.sha256(self.png.read_bytes()).digest(),before)
        self.assertEqual((out/'originals'/'001.png').read_bytes(),self.png.read_bytes())
    def test_refuse_overwrite(self):
        m=self.manifest([{'path':str(self.png),'kind':'screenshot'}]);out=create(m,self.root/'project')
        before=(out/'project.json').read_bytes()
        with self.assertRaises(FileExistsError):create(m,out)
        self.assertEqual((out/'project.json').read_bytes(),before)
    def test_no_confirmed_screenshot(self):
        with self.assertRaisesRegex(ValueError,'没有来源确认的截图'):
            create(self.manifest([{'path':'unknown.png'}]),self.root/'project')



from article import scan, refresh_binding, return_article, image_refs

class ArticleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        (self.root/'screen.png').write_bytes(self.png);(self.root/'ai.png').write_bytes(self.png)
        self.article=self.root/'article.md'
        self.original='---\r\ntitle: 测试🙂\r\n---\r\n![截图](screen.png "保留标题")\r\n![插图](ai.png)\r\n![[screen.png|600]]\r\n`![代码](screen.png)`\r\n'
        self.article.write_bytes(self.original.encode())
        spec=scan(self.article)
        for i in spec['images']:
            i['kind']='screenshot' if Path(i['path']).name=='screen.png' else 'ai-generated'
        manifest=self.root/'manifest.json';manifest.write_text(json.dumps(spec))
        self.project=create(manifest,self.root/'project')
        data=json.loads((self.project/'project.json').read_text())
        self.images=[{'id':s['id'],'png':'data:image/png;base64,'+base64.b64encode(self.png).decode()} for s in data['slides']]
    def test_return_and_repeat_preserve_prose_ai_and_size(self):
        self.assertEqual(len(image_refs(self.original)),3)
        result=return_article(self.project,self.images)
        updated=self.article.read_bytes().decode()
        self.assertEqual(result['mode'],'new-batch')
        self.assertEqual(result['count'],2)
        self.assertIn('![插图](ai.png)',updated);self.assertIn('|600]]',updated);self.assertIn('"保留标题")',updated)
        self.assertIn('`![代码](screen.png)`',updated)
        self.assertEqual(Path(result['backup']).read_bytes(),self.original.encode())
        refs=image_refs(updated);original_refs=image_refs(self.original)
        normalized=updated
        for new,old in reversed(list(zip(refs,original_refs))):normalized=normalized[:new['start']]+old['original']+normalized[new['end']:]
        self.assertEqual(normalized,self.original)
        returned_file=Path(result['assets'])/'s001-annotated.png'
        first_bytes=returned_file.read_bytes()
        changed=b'\x89PNG\r\n\x1a\nchanged-render'
        changed_images=[{'id':item['id'],'png':'data:image/png;base64,'+base64.b64encode(changed).decode()} for item in self.images]
        second=return_article(self.project,changed_images)
        self.assertEqual(second['mode'],'overwrite')
        self.assertEqual(second['assets'],result['assets'])
        self.assertEqual(self.article.read_bytes().decode(),updated)
        self.assertEqual(returned_file.read_bytes(),changed)
        self.assertEqual((Path(second['image_backup'])/returned_file.name).read_bytes(),first_bytes)
        self.assertEqual(Path(second['backup']).read_bytes().decode(),updated)
    def test_external_prose_change_is_preserved(self):
        self.article.write_bytes((self.original+'新增正文').encode())
        result=return_article(self.project,self.images)
        self.assertEqual(result['count'],2)
        self.assertEqual(result['skipped'],0)
        self.assertTrue(self.article.read_bytes().decode().endswith('新增正文'))
    def test_partial_duplicate_ref_is_refused(self):
        self.article.write_text(self.original.replace('![[screen.png|600]]\r\n',''))
        with self.assertRaisesRegex(ValueError,'同名截图被部分删除'):return_article(self.project,self.images)
        self.assertNotIn('screenshot-assets',self.article.read_text())
    def test_incomplete_batch_refused(self):
        with self.assertRaisesRegex(ValueError,'缺少文章仍在使用的截图'):return_article(self.project,self.images[:1])
        self.assertEqual(self.article.read_bytes(),self.original.encode())

    def test_deleted_unique_ref_is_skipped_and_new_content_survives(self):
        root=self.root/'unique';root.mkdir()
        for name in ('one.png','two.png','new.png'):(root/name).write_bytes(self.png)
        article=root/'article.md';article.write_text('开头\n![[one.png]]\n中间\n![[two.png]]\n结尾\n')
        spec=scan(article,root)
        for item in spec['images']:item['kind']='screenshot'
        manifest=root/'manifest.json';manifest.write_text(json.dumps(spec))
        project=create(manifest,root/'project');data=json.loads((project/'project.json').read_text())
        images=[{'id':s['id'],'png':'data:image/png;base64,'+base64.b64encode(self.png).decode()} for s in data['slides']]
        article.write_text('新增正文\n![[new.png]]\n![[one.png]]\n结尾\n')
        result=return_article(project,images)
        updated=article.read_text()
        self.assertEqual((result['count'],result['skipped'],result['removed_ids']),(1,1,['s002']))
        self.assertIn('新增正文',updated);self.assertIn('![[new.png]]',updated);self.assertNotIn('two.png',updated)
        self.assertIn('s001-annotated.png',updated)

    def test_refresh_binding_prunes_deleted_unique_slide(self):
        root=self.root/'rebind';root.mkdir()
        for name in ('one.png','two.png'):(root/name).write_bytes(self.png)
        article=root/'article.md';article.write_text('![[one.png]]\n![[two.png]]\n')
        spec=scan(article,root)
        for item in spec['images']:item['kind']='screenshot'
        manifest=root/'manifest.json';manifest.write_text(json.dumps(spec))
        project=create(manifest,root/'project')
        article.write_text('前言已修改\n![[one.png]]\n')
        result=refresh_binding(project);data=json.loads((project/'project.json').read_text())
        self.assertEqual((result['slides'],result['removed_ids']),(1,['s002']))
        self.assertEqual([s['id'] for s in data['slides']],['s001'])
        self.assertEqual(data['slides'][0]['annotations'],[])
        self.assertEqual(article.read_text(),'前言已修改\n![[one.png]]\n')

    def test_vault_paths(self):
        nested=self.root/'notes';nested.mkdir()
        article=nested/'note.md';article.write_text('正文\n![[screen.png|500]]')
        spec=scan(article,self.root)
        for item in spec['images']:item['kind']='screenshot'
        manifest=self.root/'vault.json';manifest.write_text(json.dumps(spec))
        project=create(manifest,self.root/'vault-project')
        data=json.loads((project/'project.json').read_text())
        result=return_article(project,[{'id':data['slides'][0]['id'],'png':self.images[0]['png']}])
        self.assertIn('![[notes/screenshot-assets/',article.read_text())
        self.assertIn('|500]]',article.read_text())

    def test_parentheses_and_fences(self):
        text='```md\n![skip](x.png)\n```\n![real](folder/a(b).png "说明")\n'
        refs=image_refs(text)
        self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]['original'],'folder/a(b).png')

class ExportTests(unittest.TestCase):
    def test_single_batch_and_safe_paths(self):
        from editor import export_files, exported_path
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            png='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\nexample').decode()
            single=export_files(root, {'images':[{'png':png}], 'single':True})
            batch=export_files(root, {'images':[{'png':png}]*2})
            self.assertNotEqual(single['path'],batch['path'])
            self.assertTrue(single['download'].endswith('.png'))
            self.assertTrue(batch['download'].endswith('.zip'))
            with zipfile.ZipFile(Path(batch['path'])/'screenshots.zip') as z:
                self.assertEqual(set(z.namelist()), {'001-annotated.png','002-annotated.png','mapping.json'})
            self.assertTrue(exported_path(root,single['batch']).is_dir())
            for invalid in ('../project.json','/etc/passwd'):
                with self.assertRaises(ValueError): exported_path(root,invalid)
            before=list((root/'exports').iterdir())
            with self.assertRaises(ValueError): export_files(root,{'images':[{'png':'data:image/png;base64,YmFk'}]})
            self.assertEqual(before,list((root/'exports').iterdir()))

class EditorUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(Path(__file__).resolve().parents[1]/'assets'/'editor.html').read_text()

    def test_mosaic_editor_contract(self):
        for marker in ('data-tool="mosaic"','function paintMosaic',"type==='mosaic'",'data-mosaic="12"','data-mosaic="20"','data-mosaic="32"'):
            self.assertIn(marker,self.html)
        self.assertLess(self.html.index("filter(a=>a.type==='mosaic')"),self.html.index('slide.annotations.forEach'))

    def test_annotation_and_watermark_defaults(self):
        self.assertIn("function annotationFontSize(a){return a.fontSize||(a.type==='text'?48:28)}",self.html)
        self.assertIn("fontSize:tool==='text'?48:28",self.html)
        self.assertIn("function watermark(slide){return {enabled:!!project.defaultWatermark,size:182,position:'right'",self.html)
        self.assertIn('<option value="152">较大</option><option value="182">大</option>',self.html)
        self.assertIn('function font(c,size,weight=600)',self.html)
        self.assertIn("font(c,size,a.type==='text'?400:600)",self.html)
        self.assertIn('font(ctx,size,400)',self.html)

if __name__=='__main__':unittest.main()
