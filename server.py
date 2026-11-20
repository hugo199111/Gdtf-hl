from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import fitz, re, io, zipfile, xml.etree.ElementTree as ET
app = FastAPI(title="HL GDTF Builder")
def guess(s):
 s=s.lower()
 for key,attr in [("pan","Pan"),("tilt","Tilt"),("dimmer","Dimmer"),("intensity","Dimmer"),("shutter","Shutter1"),("strobe","Shutter1"),("gobo","Gobo1"),("color","Color1"),("colour","Color1"),("prism","Prism1"),("focus","Focus1"),("zoom","Zoom"),("iris","Iris")]:
  if key in s:return attr
 return "Dimmer"
@app.post("/api/parse")
async def parse(file: UploadFile=File(...)):
 if not (file.filename or "").lower().endswith(".pdf"):raise HTTPException(400,"Seleccioná un PDF")
 raw=await file.read()
 if len(raw)>20_000_000:raise HTTPException(413,"PDF demasiado grande")
 try:
  with fitz.open(stream=raw,filetype="pdf") as doc:
   pages=len(doc); content="\n".join(p.get_text() for p in doc)
 except Exception:raise HTTPException(400,"No se pudo leer el PDF")
 found={}
 for line in content.splitlines():
  m=re.match(r"^\s*(?:CH(?:ANNEL)?\s*)?(\d{1,3})\s*[-.:|)]?\s+(.{3,65})$",line,re.I)
  if m:
   n=int(m.group(1));name=m.group(2).strip()
   if 1<=n<=128 and n not in found:found[n]={"channel":n,"name":name,"attribute":guess(name),"confidence":"low"}
 return {"pages":pages,"channels":[found[n] for n in sorted(found)],"warning":"Detección orientativa. Revisá todos los canales con el manual. PDFs escaneados no se leen."}
class Channel(BaseModel):
 offset:int
 name:str
 attribute:str="Dimmer"
 default:int=0
class Fixture(BaseModel):
 manufacturer:str="HL"
 name:str
 mode:str="Standard"
 channels:list[Channel]
@app.post("/api/export")
def export(f:Fixture):
 if not f.channels or len(f.channels)>512 or not f.name.strip():raise HTTPException(400,"Nombre y canales requeridos")
 if any(c.offset<1 or c.offset>512 or c.default<0 or c.default>255 for c in f.channels):raise HTTPException(400,"Valores fuera de rango")
 if len({c.offset for c in f.channels})!=len(f.channels):raise HTTPException(400,"Offsets duplicados")
 root=ET.Element("GDTF",DataVersion="1.2")
 ft=ET.SubElement(root,"FixtureType",Name=f.name,ShortName=f.name,LongName=f.name,Manufacturer=f.manufacturer,Description="HL GDTF Builder MVP - experimental",FixtureTypeID="00000000-0000-4000-8000-000000000001")
 defs=ET.SubElement(ft,"AttributeDefinitions");ET.SubElement(defs,"ActivationGroups");ET.SubElement(defs,"FeatureGroups");attrs=ET.SubElement(defs,"Attributes")
 for a in dict.fromkeys(c.attribute for c in f.channels):ET.SubElement(attrs,"Attribute",Name=a,Pretty=a,PhysicalUnit="None")
 models=ET.SubElement(ft,"Models");ET.SubElement(models,"Model",Name="Body",Length="0.3",Width="0.3",Height="0.3",PrimitiveType="Cube")
 geo=ET.SubElement(ft,"Geometries");ET.SubElement(geo,"Geometry",Name="Body",Model="Body",Position="{1,0,0,0}{0,1,0,0}{0,0,1,0}{0,0,0,1}")
 modes=ET.SubElement(ft,"DMXModes");mode=ET.SubElement(modes,"DMXMode",Name=f.mode,Geometry="Body");channels=ET.SubElement(mode,"DMXChannels")
 for c in sorted(f.channels,key=lambda c:c.offset):
  ch=ET.SubElement(channels,"DMXChannel",DMXBreak="1",Offset=str(c.offset),Default=f"{c.default}/1",Highlight="255/1",Geometry="Body")
  logical=ET.SubElement(ch,"LogicalChannel",Attribute=c.attribute)
  ET.SubElement(logical,"ChannelFunction",Name=c.name,Attribute=c.attribute,DMXFrom="0/1",PhysicalFrom="0",PhysicalTo="1")
 ET.SubElement(ft,"Protocols")
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:z.writestr("description.xml",ET.tostring(root,encoding="utf-8",xml_declaration=True))
 buf.seek(0)
 safe=re.sub(r"[^A-Za-z0-9_-]","_",f.name)[:50]
 return StreamingResponse(buf,media_type="application/octet-stream",headers={"Content-Disposition":f'attachment; filename="{safe}.gdtf"'})
app.mount("/",StaticFiles(directory="static",html=True),name="static")
