#!/usr/bin/env python3
# V01D RADIO v1.0 — single-file AM/FM synthesizer | pip install pyaudio (optional)
import tkinter as tk,threading,math,random,struct,json,os,sys,time,subprocess
try:
    import pyaudio;_PA=pyaudio.PyAudio();AB="pyaudio"
except:
    _PA=None
    try:subprocess.run(["aplay","--version"],capture_output=True);AB="aplay" if sys.platform.startswith("linux") else "none"
    except:AB="none"
RATE=44100;CHUNK=1024
FMS={88.1:("VOID DRONE","drone",55.,[1,1.5,2.,3.]),91.9:("RETRO WAVE","melody",220.,[1,1.25,1.5,2.]),
     94.5:("DEEP SPACE","pad",40.,[1,2.,2.5,4.]),98.5:("STATIC FC","static",0.,[]),
     101.1:("BASS HORIZON","bass",80.,[1,1.5,2.]),103.7:("CYBER PULSE","pulse",330.,[1,2.,4.]),
     106.3:("AMBER SIG","melody",440.,[1,1.2,1.5]),107.9:("ENTROPY","chaos",160.,[1,1.33,1.77])}
AMS={660:("VOID WAVE AM","drone",60.,[1,2.,3.]),820:("AM STATIC","static",0.,[]),
     1010:("RETRO AM","melody",110.,[1,1.25,1.5]),1190:("DEEP AM","bass",50.,[1,2.]),
     1390:("PULSE AM","pulse",220.,[1,2.]),1550:("GHOST SIG","pad",80.,[1,1.5,2.5])}
BG="#070707";PN="#0d0d0d";FG="#00ff41";DM="#004a18";AM="#ff9900";RD="#ff2200";BD="#1c1c1c";DK="#001a08"
PF=os.path.join(os.path.expanduser("~"),".v01d_radio.json")

class Engine(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.freq=98.5;self.mode="FM";self.vol=0.6;self.sql=0.08
        self.running=False;self.sig=0.0;self.name="--- SCANNING ---"
        self._t=0.;self._mt=0.;self._lk=threading.Lock()
    def sf(self,f):
        with self._lk:self.freq=f
    def sm(self,m):
        with self._lk:self.mode=m;self._t=0.;self._mt=0.
    def sv(self,v):
        with self._lk:self.vol=max(0.,min(1.,v))
    def sq(self,s):
        with self._lk:self.sql=max(0.,min(1.,s))
    def _csig(self,d,st):
        bw=0.25 if self.mode=="FM" else 8.
        best=0.;bsta=None
        for sf,info in st.items():
            s=math.exp(-(abs(d-sf)**2)/(2*(bw*.5)**2))
            if s>best:best=s;bsta=info
        return best,bsta
    def _samp(self,kind,base,chord,t,mt):
        if kind=="static":return random.uniform(-1.,1.)*0.4
        elif kind=="drone":
            s=sum((1/(i+1))*math.sin(2*math.pi*base*r*t+.03*math.sin(2*math.pi*.07*(t+i*1.3)))for i,r in enumerate(chord))
            return s*0.35
        elif kind=="pad":
            s=sum((.5/(i+1))*math.sin(2*math.pi*base*r*(t+.002*math.sin(2*math.pi*5.5*t)))for i,r in enumerate(chord))
            return math.tanh(s*.9)*.4
        elif kind=="melody":
            P=[1.,1.125,1.25,1.5,1.667,2.,2.25];note=P[int(mt*1.8)%len(P)]
            return .45*abs(math.sin(math.pi*(mt*1.8%1.)))*math.sin(2*math.pi*base*note*t)
        elif kind=="bass":
            s=sum((1/(i+1))*math.sin(2*math.pi*base*r*t)for i,r in enumerate(chord))
            return math.tanh(s*1.8)*.4
        elif kind=="pulse":
            ph=(t*base)%1.;pw=.3+.1*math.sin(2*math.pi*.3*t)
            return(.35 if ph<pw else-.35)+.08*math.sin(2*math.pi*base*2*t)
        elif kind=="chaos":
            r1=math.sin(2*math.pi*base*t);r2=math.sin(2*math.pi*base*1.333*t+r1*.5)
            return math.tanh(math.sin(2*math.pi*base*1.777*t+r2*.7))*.35
        return 0.
    def _chunk(self):
        with self._lk:f=self.freq;m=self.mode;v=self.vol;sq=self.sql
        st=FMS if m=="FM" else AMS;sig,sta=self._csig(f,st)
        self.sig=sig;self.name=sta[0] if sta and sig>sq else "--- SCANNING ---"
        dt=1./RATE;buf=[];t=self._t;mt=self._mt
        if sta and sig>sq:
            _,kind,base,chord=sta
            for _ in range(CHUNK):
                s=self._samp(kind,base,chord,t,mt)
                s=(s*sig+random.uniform(-1,1)*.15*(1-sig))*v
                buf.append(int(max(-.999,min(.999,s))*32767));t+=dt;mt+=dt
        else:
            for _ in range(CHUNK):
                s=random.uniform(-1,1)*.1*v*sig if sig>sq*.5 else 0.
                buf.append(int(s*32767));t+=dt
        self._t=t;self._mt=mt
        return struct.pack(f"<{CHUNK}h",*buf)
    def run(self):
        self.running=True
        if AB=="pyaudio":
            st=_PA.open(format=pyaudio.paInt16,channels=1,rate=RATE,output=True,frames_per_buffer=CHUNK)
            while self.running:
                try:st.write(self._chunk())
                except:break
            st.stop_stream();st.close()
        elif AB=="aplay":
            p=subprocess.Popen(["aplay","-r",str(RATE),"-f","S16_LE","-c","1","-"],
                               stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
            while self.running:
                try:p.stdin.write(self._chunk());p.stdin.flush()
                except:break
            p.stdin.close();p.terminate()
        else:
            while self.running:self._chunk();time.sleep(CHUNK/RATE)
    def stop(self):self.running=False

class Knob(tk.Canvas):
    def __init__(self,master,mn,mx,iv,cb,sz=180,**kw):
        super().__init__(master,width=sz,height=sz,bg=BG,highlightthickness=0,**kw)
        self.mn=mn;self.mx=mx;self.v=iv;self.cb=cb;self.sz=sz
        self._dy=None;self._dv=None
        self.bind("<ButtonPress-1>",self._p);self.bind("<B1-Motion>",self._d)
        self.bind("<MouseWheel>",self._w);self.bind("<Button-4>",lambda e:self._s(1))
        self.bind("<Button-5>",lambda e:self._s(-1));self.draw()
    def _a(self,v):return -225+(v-self.mn)/(self.mx-self.mn)*270
    def draw(self):
        self.delete("all");cx=cy=self.sz/2;r=self.sz/2-8
        self.create_oval(cx-r-4,cy-r-4,cx+r+4,cy+r+4,outline=BD,width=2,fill=DK)
        self.create_oval(cx-r,cy-r,cx+r,cy+r,outline=DM,width=1,fill=PN)
        for i in range(11):
            a=math.radians(-225+i/10*270)
            x1=cx+(r-2)*math.cos(a);y1=cy+(r-2)*math.sin(a)
            x2=cx+(r-10)*math.cos(a);y2=cy+(r-10)*math.sin(a)
            self.create_line(x1,y1,x2,y2,fill=FG if i%5==0 else DM,width=1)
        a=math.radians(self._a(self.v))
        nx=cx+(r-14)*math.cos(a);ny=cy+(r-14)*math.sin(a)
        self.create_line(cx,cy,nx,ny,fill=DM,width=5)
        self.create_line(cx,cy,nx,ny,fill=AM,width=2)
        self.create_oval(cx-5,cy-5,cx+5,cy+5,fill=AM,outline="")
        self.create_oval(nx-3,ny-3,nx+3,ny+3,fill=FG,outline="")
    def _p(self,e):self._dy=e.y;self._dv=self.v
    def _d(self,e):
        if self._dy is None:return
        self.set((self._dy-e.y)/self.sz*(self.mx-self.mn)+self._dv)
    def _w(self,e):self.set(self.v+(self.mx-self.mn)/200*(e.delta/120))
    def _s(self,d):self.set(self.v+d*(self.mx-self.mn)/200)
    def set(self,v):self.v=max(self.mn,min(self.mx,v));self.draw();self.cb(self.v)

class App:
    def __init__(self,root):
        self.root=root;root.title("V01D RADIO v1.0");root.configure(bg=BG);root.resizable(False,False)
        self.mode=tk.StringVar(value="FM");self.ffm=98.5;self.fam=1010.
        self.presets=self._lp();self.eng=Engine();self._build();self._go()
        root.protocol("WM_DELETE_WINDOW",self._quit)
    def _lp(self):
        try:
            with open(PF)as f:return json.load(f)
        except:return{str(i):None for i in range(1,11)}
    def _sp(self):
        try:
            with open(PF,"w")as f:json.dump(self.presets,f)
        except:pass
    def _build(self):
        P=8
        t=tk.Frame(self.root,bg=BG);t.pack(fill="x",padx=P,pady=(P,0))
        tk.Label(t,text="V01D RADIO",font=("Courier",16,"bold"),bg=BG,fg=FG).pack(side="left")
        mf=tk.Frame(t,bg=BG);mf.pack(side="right")
        for m in("AM","FM"):
            tk.Radiobutton(mf,text=m,variable=self.mode,value=m,command=self._mc,
                bg=BG,fg=FG,selectcolor=DK,activebackground=BG,activeforeground=AM,
                font=("Courier",10,"bold"),indicatoron=0,width=4,relief="flat",
                highlightthickness=1,highlightbackground=BD).pack(side="left",padx=1)
        tk.Label(t,text=f"[{AB.upper()}]",font=("Courier",7),bg=BG,fg=FG if AB!="none" else RD).pack(side="right",padx=6)
        tk.Frame(self.root,bg=BD,height=1).pack(fill="x",padx=P,pady=3)
        d=tk.Frame(self.root,bg=PN);d.pack(fill="x",padx=P,pady=1)
        self.ls=tk.Label(d,text="--- SCANNING ---",font=("Courier",11,"bold"),bg=PN,fg=AM,width=22,anchor="w")
        self.ls.pack(side="left",padx=6,pady=3)
        self.lf=tk.Label(d,text="98.5 MHz",font=("Courier",20,"bold"),bg=PN,fg=FG,anchor="e")
        self.lf.pack(side="right",padx=8,pady=2)
        self.bc=tk.Canvas(self.root,bg=DK,height=26,highlightthickness=0)
        self.bc.pack(fill="x",padx=P,pady=2)
        self.bc.bind("<Configure>",lambda e:self._db());self.bc.bind("<ButtonPress-1>",self._bck);self.bc.bind("<B1-Motion>",self._bck)
        mid=tk.Frame(self.root,bg=BG);mid.pack(padx=P,pady=4)
        kf=tk.Frame(mid,bg=BG);kf.pack(side="left",padx=(0,12))
        tk.Label(kf,text="TUNE",font=("Courier",7),bg=BG,fg=DM).pack()
        self.knob=Knob(kf,87.5,108.,98.5,self._kc,size=175);self.knob.pack()
        rf=tk.Frame(mid,bg=BG);rf.pack(side="left",fill="y")
        tk.Label(rf,text="SIGNAL",font=("Courier",7),bg=BG,fg=DM).pack(anchor="w")
        self.sc=tk.Canvas(rf,width=195,height=18,bg=PN,highlightthickness=0);self.sc.pack(pady=(0,6))
        self._sl(rf,"VOLUME",0.,1.,.6,lambda v:self.eng.sv(float(v)))
        self._sl(rf,"SQUELCH",0.,.5,.08,lambda v:self.eng.sq(float(v)))
        tk.Label(rf,text="FREQ",font=("Courier",7),bg=BG,fg=DM).pack(anchor="w",pady=(6,0))
        ef=tk.Frame(rf,bg=BG);ef.pack(fill="x")
        self.fe=tk.Entry(ef,font=("Courier",10),bg=PN,fg=FG,insertbackground=FG,
                         relief="flat",width=9,highlightthickness=1,highlightbackground=BD)
        self.fe.insert(0,"98.5");self.fe.pack(side="left",padx=(0,3));self.fe.bind("<Return>",self._et)
        tk.Button(ef,text="GO",font=("Courier",8,"bold"),bg=DK,fg=FG,activebackground=DM,
                  activeforeground=AM,relief="flat",bd=0,padx=5,pady=1,command=self._et).pack(side="left")
        sf=tk.Frame(rf,bg=BG);sf.pack(fill="x",pady=3)
        for txt,dd in(("◄◄",-.2),("◄",-.1),("►",.1),("►►",.2)):
            tk.Button(sf,text=txt,font=("Courier",8,"bold"),bg=PN,fg=FG,relief="flat",
                      bd=0,padx=4,pady=1,activebackground=DM,activeforeground=AM,
                      command=lambda x=dd:self._step(x)).pack(side="left",padx=1)
        tk.Button(sf,text="SCAN",font=("Courier",8,"bold"),bg=PN,fg=AM,relief="flat",
                  bd=0,padx=4,pady=1,activebackground=DM,activeforeground=FG,
                  command=self._scan).pack(side="right")
        tk.Frame(self.root,bg=BD,height=1).pack(fill="x",padx=P,pady=3)
        tk.Label(self.root,text="PRESETS  L-click=load  R-click=save",font=("Courier",7),bg=BG,fg=DM).pack(anchor="w",padx=P)
        pf=tk.Frame(self.root,bg=BG);pf.pack(padx=P,pady=(2,P))
        self.pb={}
        for i in range(1,11):
            k=str(i);data=self.presets.get(k)
            b=tk.Button(pf,text=self._pl(data),font=("Courier",7),width=8,
                        bg=PN if data else DK,fg=FG if data else DM,
                        activebackground=DM,activeforeground=AM,relief="flat",bd=0,pady=3)
            b.grid(row=0,column=i-1,padx=1)
            b.bind("<ButtonPress-1>",lambda e,x=k:self._loadp(x))
            b.bind("<ButtonPress-3>",lambda e,x=k:self._savep(x))
            b.bind("<Button-2>",lambda e,x=k:self._savep(x))
            self.pb[k]=b
        tk.Frame(self.root,bg=BD,height=1).pack(fill="x",padx=P,pady=1)
        self.sh=tk.Label(self.root,text=self._hint(),font=("Courier",7),bg=BG,fg=DM,anchor="w")
        self.sh.pack(fill="x",padx=P,pady=(1,P))
        self.root.update_idletasks();self._db()
    def _sl(self,p,label,mn,mx,iv,cmd):
        tk.Label(p,text=label,font=("Courier",7),bg=BG,fg=DM).pack(anchor="w")
        s=tk.Scale(p,from_=mn,to=mx,resolution=(mx-mn)/200,orient="horizontal",command=cmd,
                   bg=BG,fg=FG,troughcolor=PN,activebackground=AM,highlightthickness=0,
                   sliderrelief="flat",bd=0,length=195,showvalue=0)
        s.set(iv);s.pack(fill="x",pady=(0,5));return s
    def _hint(self):
        st=FMS if self.mode.get()=="FM" else AMS;u="M"if self.mode.get()=="FM"else"k"
        return"  ".join(f"{f}{u}={v[0]}"for f,v in sorted(st.items()))
    def _db(self,*_):
        c=self.bc;w=c.winfo_width();h=26
        if w<2:return
        c.delete("all");c.create_rectangle(0,0,w,h,fill=DK,outline="")
        m=self.mode.get();mn=87.5 if m=="FM" else 530;mx=108. if m=="FM" else 1700
        u="MHz"if m=="FM"else"kHz";st=FMS if m=="FM" else AMS;cur=self.ffm if m=="FM" else self.fam
        def fx(f):return(f-mn)/(mx-mn)*w
        for sf,info in st.items():
            x=fx(sf);c.create_rectangle(x-2,5,x+2,h-2,fill=DM,outline="")
            c.create_text(x,2,text=info[0][:5],fill=DM,font=("Courier",5),anchor="n")
        nx=fx(cur);c.create_line(nx,0,nx,h,fill=AM,width=2)
        c.create_polygon(nx-4,0,nx+4,0,nx,7,fill=AM,outline="")
        c.create_text(3,h//2,text=f"{mn}{u}",fill=DM,font=("Courier",6),anchor="w")
        c.create_text(w-3,h//2,text=f"{mx}{u}",fill=DM,font=("Courier",6),anchor="e")
    def _dsig(self,sig):
        c=self.sc;w=c.winfo_width();h=18;c.delete("all")
        c.create_rectangle(0,0,w,h,fill=PN,outline="")
        n=18
        for i in range(n):
            p=(i+1)/n;x1=i*(w/n);x2=x1+w/n-1
            col=(FG if p<.7 else(AM if p<.9 else RD))if p<=sig else BD
            c.create_rectangle(x1+1,3,x2,h-3,fill=col,outline="")
    def _setf(self,f):
        m=self.mode.get()
        if m=="FM":f=max(87.5,min(108.,f));self.ffm=f;self.knob.mn=87.5;self.knob.mx=108.
        else:f=max(530,min(1700,f));self.fam=f;self.knob.mn=530;self.knob.mx=1700
        self.knob.v=f;self.knob.draw()
        u="MHz"if m=="FM"else"kHz";self.lf.config(text=f"{f:.1f} {u}")
        self.fe.delete(0,"end");self.fe.insert(0,f"{f:.1f}")
        self.eng.sf(f);self._db()
    def _kc(self,v):self._setf(v)
    def _et(self,*_):
        try:self._setf(float(self.fe.get()))
        except:pass
    def _step(self,d):
        m=self.mode.get();cur=self.ffm if m=="FM" else self.fam
        self._setf(cur+(d*10 if m=="AM" else d))
    def _mc(self,force_freq=None):
        m=self.mode.get();self.eng.sm(m)
        if m=="FM":self.knob.mn=87.5;self.knob.mx=108.
        else:self.knob.mn=530;self.knob.mx=1700
        f=force_freq if force_freq else(self.ffm if m=="FM" else self.fam)
        self._setf(f);self.sh.config(text=self._hint())
    def _bck(self,e):
        w=self.bc.winfo_width();m=self.mode.get()
        mn=87.5 if m=="FM" else 530;mx=108. if m=="FM" else 1700
        self._setf(mn+(e.x/w)*(mx-mn))
    def _pl(self,data):
        if not data:return"[EMPTY]"
        mo,fr=data;u="M"if mo=="FM"else"k";return f"[{mo}]{fr:.1f}{u}"
    def _savep(self,k):
        m=self.mode.get();f=self.ffm if m=="FM" else self.fam
        self.presets[k]=[m,round(f,1)];self._sp()
        self.pb[k].config(text=self._pl(self.presets[k]),bg=PN,fg=FG)
    def _loadp(self,k):
        d=self.presets.get(k)
        if not d:return
        mo,fr=d;self.mode.set(mo);self._mc(force_freq=fr)
    def _scan(self):
        m=self.mode.get();st=FMS if m=="FM" else AMS
        freqs=sorted(st.keys());cur=self.ffm if m=="FM" else self.fam
        nxt=next((f for f in freqs if f>cur+.05),freqs[0]);self._setf(nxt)
    def _meter(self):
        if self.eng.running:self.ls.config(text=self.eng.name[:22]);self._dsig(self.eng.sig)
        self.root.after(120,self._meter)
    def _go(self):self.eng.start();self.root.after(200,self._meter)
    def _quit(self):self.eng.stop();self.root.destroy()

if __name__=="__main__":
    if AB=="none":print("No audio backend. pip install pyaudio for sound. GUI still runs.")
    root=tk.Tk();App(root);root.mainloop()
