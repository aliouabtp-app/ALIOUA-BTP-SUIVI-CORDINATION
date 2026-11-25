import {useEffect,useRef,useState} from "react";
import * as THREE from "three";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";
import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";

export default function Model3DViewer({url}){
 const host=useRef(null);
 const [error,setError]=useState("");
 useEffect(()=>{
  const root=host.current;
  if(!root||!url)return;
  setError("");
  const scene=new THREE.Scene();
  scene.background=new THREE.Color(0xf1f6f8);
  const camera=new THREE.PerspectiveCamera(45,1,0.01,10000);
  camera.position.set(8,7,9);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  root.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xffffff,0x718596,2.1));
  const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(6,10,7);scene.add(key);
  const grid=new THREE.GridHelper(40,40,0x9eb2bf,0xd8e3e9);scene.add(grid);
  const controls=new OrbitControls(camera,renderer.domElement);
  controls.enableDamping=true;controls.dampingFactor=0.07;
  let frame=0,model=null;
  const resize=()=>{
   const w=Math.max(root.clientWidth,320),h=Math.max(root.clientHeight,300);
   camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);
  };
  const observer=new ResizeObserver(resize);observer.observe(root);resize();
  new GLTFLoader().load(url,gltf=>{
   model=gltf.scene;scene.add(model);
   const bounds=new THREE.Box3().setFromObject(model);
   const size=bounds.getSize(new THREE.Vector3());
   const center=bounds.getCenter(new THREE.Vector3());
   model.position.sub(center);
   const max=Math.max(size.x,size.y,size.z,1);
   camera.position.set(max*1.5,max*1.2,max*1.5);
   camera.near=Math.max(max/1000,0.001);camera.far=max*100;camera.updateProjectionMatrix();
   controls.target.set(0,0,0);controls.update();
  },undefined,()=>setError("تعذر تحميل النموذج. تحقق من رابط الملف وصلاحية الوصول."));
  const animate=()=>{frame=requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);};
  animate();
  return ()=>{
   cancelAnimationFrame(frame);observer.disconnect();controls.dispose();
   scene.traverse(o=>{if(o.geometry)o.geometry.dispose();if(o.material){if(Array.isArray(o.material))o.material.forEach(m=>m.dispose());else o.material.dispose();}});
   renderer.dispose();if(renderer.domElement.parentNode===root)root.removeChild(renderer.domElement);
  };
 },[url]);
 return <div className="model3d-viewer"><div className="model3d-toolbar"><span>عرض ثلاثي الأبعاد · GLB</span><small>اسحب للدوران · عجلة الفأرة للتقريب</small></div><div className="model3d-canvas" ref={host}>{error&&<p className="workspace-message">{error}</p>}</div></div>;
}
