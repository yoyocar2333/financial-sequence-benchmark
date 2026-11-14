"""Refresh an editable DOCX TOC and export PDF with an isolated LibreOffice profile.
Requires a local UNO-enabled Python and LibreOffice; never touches other profiles.
"""
import argparse,json,os,subprocess,time,uuid
from pathlib import Path
import uno
from com.sun.star.beans import PropertyValue

def prop(k,v):p=PropertyValue();p.Name=k;p.Value=v;return p

def main(out,program,registry):
 out=out.resolve();program=program.resolve();pipe='e9a_'+uuid.uuid4().hex
 (out/'logs').mkdir(exist_ok=True);(out/'checks').mkdir(exist_ok=True)
 profile=out/'render_profile';profile.mkdir(exist_ok=True)
 args=[str(program/'soffice.bin'),'-env:UserInstallation='+profile.as_uri()]
 if registry:
  uri=registry.resolve().as_uri();args+=['-env:CONFIGURATION_LAYERS=xcsxcu:'+uri+' res:'+uri]
 args+=['-env:LO_LIB_DIR='+program.as_uri(),'-env:BRAND_BASE_DIR='+program.parent.as_uri(),'-env:URE_MORE_SERVICES='+program.as_uri()+'/services/services.rdb','--headless','--nologo','--nodefault','--nofirststartwizard','--accept=pipe,name='+pipe+';urp;StarOffice.ServiceManager']
 env=dict(os.environ)
 for k in ['PYTHONPATH','URE_BOOTSTRAP','UNO_TYPES','UNO_SERVICES','URE_MORE_SERVICES','URE_MORE_TYPES','SAL_USE_VCLPLUGIN']:env.pop(k,None)
 log=(out/'logs/render.log').open('a');server=subprocess.Popen(args,env=env,stdout=log,stderr=log)
 try:
  local=uno.getComponentContext();resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local);remote=None
  for n in range(120):
   try:remote=resolver.resolve('uno:pipe,name='+pipe+';urp;StarOffice.ComponentContext');break
   except Exception:
    if server.poll() is not None:
     if server.returncode==81 and n<15:server=subprocess.Popen(args,env=env,stdout=log,stderr=log)
     else:raise RuntimeError('Isolated LibreOffice exited '+str(server.returncode))
    time.sleep(.3)
  if remote is None:raise RuntimeError('Isolated UNO connection timeout')
  desktop=remote.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',remote)
  doc=desktop.loadComponentFromURL((out/'PAPER_DRAFT.docx').as_uri(),'_blank',0,(prop('Hidden',True),prop('ReadOnly',False),prop('UpdateDocMode',3),prop('MacroExecutionMode',uno.getConstantByName('com.sun.star.document.MacroExecMode.NEVER_EXECUTE'))))
  if doc is None:raise RuntimeError('DOCX did not load')
  for _ in range(3):
   doc.refresh();doc.getTextFields().refresh()
   indexes=doc.getDocumentIndexes()
   for i in range(indexes.getCount()):indexes.getByIndex(i).update()
  pages=doc.getCurrentController().PageCount
  doc.storeAsURL((out/'PAPER_DRAFT.docx').as_uri(),(prop('FilterName','Office Open XML Text'),prop('Overwrite',True)))
  doc.storeToURL((out/'PAPER_DRAFT.pdf').as_uri(),(prop('FilterName','writer_pdf_Export'),prop('Overwrite',True),prop('FilterData',uno.Any('[]com.sun.star.beans.PropertyValue',(prop('UseTaggedPDF',True),prop('ExportBookmarks',True),prop('EmbedStandardFonts',True))))))
  doc.close(True);desktop.terminate()
  (out/'checks/render_result.json').write_text(json.dumps({'pages':pages,'toc_refreshed':True,'page_fields_refreshed':True,'renderer':'existing isolated LibreOffice UNO','financial_training':False},indent=2)+'\n')
 finally:
  if server.poll() is None:server.terminate()
  log.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--program',type=Path,required=True);p.add_argument('--registry',type=Path);a=p.parse_args();main(a.out,a.program,a.registry)
