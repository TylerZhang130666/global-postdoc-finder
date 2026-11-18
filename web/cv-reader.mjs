// File bytes remain in this browser. No analytics, network upload or persistence.
export async function readCV(file){
  if(!file||file.size>5*1024*1024)throw new Error('请选择不超过5 MB的PDF、DOCX或TXT文件');
  const ext=file.name.split('.').at(-1).toLowerCase();
  if(!['pdf','docx','txt'].includes(ext))throw new Error('支持PDF、DOCX和TXT。旧版DOC请先另存为DOCX。');
  let text='';
  if(ext==='txt')text=await file.text();
  else if(ext==='pdf'){
    const pdfjs=await import('./vendor/pdfjs-dist/build/pdf.mjs');
    pdfjs.GlobalWorkerOptions.workerSrc=new URL('./vendor/pdfjs-dist/build/pdf.worker.mjs',import.meta.url).href;
    const task=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),isEvalSupported:false,disableFontFace:true,useSystemFonts:true,stopAtErrors:true});
    let pdf;
    try{
      pdf=await task.promise;
      if(pdf.numPages>40)throw new Error('文件超过40页，请只选择简历部分');
      for(let i=1;i<=pdf.numPages;i++){
        const page=await pdf.getPage(i),content=await page.getTextContent();
        text+=content.items.map(x=>x.str??'').join(' ')+'\n';page.cleanup();
        if(text.length>100000)break;
      }
    }finally{await task.destroy();}
  }else{
    if(!window.mammoth)await new Promise((resolve,reject)=>{
      const script=document.createElement('script');script.src=new URL('./vendor/mammoth/mammoth.browser.min.js',import.meta.url).href;script.onload=resolve;script.onerror=()=>reject(new Error('Word解析组件加载失败，请重试或使用TXT'));document.head.append(script);
    });
    const result=await window.mammoth.extractRawText({arrayBuffer:await file.arrayBuffer()});text=result.value;
  }
  text=text.slice(0,100000);
  if(text.replace(/\s/g,'').length<30)throw new Error('未读到足够文字。扫描版PDF请先转为可选中文字的PDF，或粘贴简历内容。');
  return text;
}
