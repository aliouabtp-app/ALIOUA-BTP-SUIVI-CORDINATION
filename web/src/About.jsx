import {useEffect,useState} from "react";
import axios from "axios";
import {RefreshCw} from "lucide-react";
const API=(import.meta.env.VITE_API_URL||"/api").replace(/\/$/,"");
const WEB_VERSION=typeof __APP_VERSION__!=="undefined"?__APP_VERSION__:"dev";
const WEB_COMMIT=typeof __APP_COMMIT__!=="undefined"?__APP_COMMIT__:"unknown";
const short=v=>!v||v==="unknown"?"غير معروف":String(v).slice(0,12);
const when=iso=>{try{return new Date(iso).toLocaleString("ar-MA")}catch{return iso}};
export default function About(){
 const [server,setServer]=useState(null),[checked,setChecked]=useState(""),[online,setOnline]=useState(false),[busy,setBusy]=useState(true);
 async function load(){
  setBusy(true);
  try{
   const r=await axios.get(API+"/about/",{timeout:8000});
   const at=new Date().toISOString();
   setServer(r.data);setChecked(at);setOnline(true);
   try{localStorage.setItem("abtp_about",JSON.stringify({data:r.data,at}))}catch{}
  }catch{
   setOnline(false);
   try{const c=JSON.parse(localStorage.getItem("abtp_about")||"null");if(c){setServer(c.data);setChecked(c.at)}}catch{}
  }finally{setBusy(false)}
 }
 useEffect(()=>{load()},[]);
 const rows=[["إصدار الواجهة",WEB_VERSION],["commit الواجهة",short(WEB_COMMIT)],["عنوان API",API],["إصدار الخادم",server?.version||"غير معروف"],["commit الخادم",short(server?.commit)]];
 if(checked)rows.push(["آخر فحص ناجح",when(checked)]);
 return <div className="workspace"><div className="workspace-head"><div><h2>حول التطبيق</h2><p>معلومات الإصدار لتسهيل الدعم والتحقق من النسخة المثبتة</p></div><button className="icon-btn" onClick={load} disabled={busy} title="تحديث"><RefreshCw size={18}/></button></div>
  <div className="workspace-message">{busy?"جارٍ فحص الخادم…":online?"متصل بالخادم":"غير متصل — تُعرض آخر قيم معروفة"}</div>
  <div className="data-list">{rows.map(([k,v])=><div className="data-row" key={k}><div><b>{k}</b><small dir="ltr">{v}</small></div></div>)}</div></div>
}
