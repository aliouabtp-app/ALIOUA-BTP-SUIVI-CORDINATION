import {useEffect,useRef,useState} from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc=pdfWorker;

/** يعرض الصفحة الأولى من PDF مع إحداثيات نسبية للدبابيس. */
export default function PlanPdfViewer({url,onPick,pins=[]}){
 const canvasRef=useRef(null);
 const [state,setState]=useState("loading");
 useEffect(()=>{
  let cancelled=false;let task=null;
  async function render(){
   setState("loading");
   try{
    task=pdfjsLib.getDocument({url});
    const pdf=await task.promise;
    if(cancelled)return;
    const page=await pdf.getPage(1);
    const viewport=page.getViewport({scale:1.5});
    const canvas=canvasRef.current;
    if(!canvas)return;
    const context=canvas.getContext("2d");
    canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
    await page.render({canvasContext:context,viewport}).promise;
    if(!cancelled)setState("ready");
   }catch(error){if(!cancelled)setState("error");}
  }
  render();
  return()=>{cancelled=true;if(task)task.destroy();};
 },[url]);
 function choose(e){
  if(!onPick||state!=="ready")return;
  const r=e.currentTarget.getBoundingClientRect();
  const x=Math.min(1,Math.max(0,(e.clientX-r.left)/r.width));
  const y=Math.min(1,Math.max(0,(e.clientY-r.top)/r.height));
  onPick(x,y);
 }
 return <div className="pdf-plan-shell">
  <div className="pdf-plan-toolbar"><span>PDF · الصفحة الأولى</span><span>النقر لتحديد موقع الملاحظة</span></div>
  <div className="pdf-plan-viewer">
   <canvas ref={canvasRef}/>
   {state==="ready"&&<div className="pdf-plan-overlay" onClick={choose}>
    {pins.map((pin,i)=><div key={i} className="pdf-plan-pin" style={{left:(pin.x*100)+"%",top:(pin.y*100)+"%"}} title={pin.label||"ملاحظة"}><span>!</span></div>)}
   </div>}
   {state!=="ready"&&<div className="pdf-plan-state">{state==="loading"?"جارٍ تحميل المخطط…":"تعذر عرض ملف PDF. تحقق من الملف واتصال الخادم."}</div>}
  </div>
 </div>;
}
