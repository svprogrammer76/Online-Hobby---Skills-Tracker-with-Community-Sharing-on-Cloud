"""Local-first, cloud-ready hobby tracker API. Run with: uvicorn backend.app:app --reload"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, secrets, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
DB_URL=os.getenv('DATABASE_URL',f"sqlite:///{ROOT/'tracker.db'}")
if DB_URL.startswith('postgres://'):
 DB_URL=DB_URL.replace('postgres://','postgresql+psycopg://',1)
elif DB_URL.startswith('postgresql://'):
 DB_URL=DB_URL.replace('postgresql://','postgresql+psycopg://',1)
engine=create_engine(DB_URL,connect_args={'check_same_thread':False} if DB_URL.startswith('sqlite') else {})
SessionLocal=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
SECRET=os.getenv('APP_SECRET','local-development-secret-change-me')
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR',ROOT/'uploads')); UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
def utcnow_naive():return datetime.now(timezone.utc).replace(tzinfo=None)
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__='users'
 id:Mapped[int]=mapped_column(primary_key=True); username:Mapped[str]=mapped_column(String(30),unique=True,index=True); email:Mapped[str]=mapped_column(String(254),unique=True,index=True)
 password_hash:Mapped[str]=mapped_column(String(200)); name:Mapped[str]=mapped_column(String(80)); bio:Mapped[str]=mapped_column(String(500),default=''); interests:Mapped[str]=mapped_column(String(500),default=''); profile_picture:Mapped[Optional[str]]=mapped_column(String(500),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow_naive)
class Skill(Base):
 __tablename__='skills'
 id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); skill_name:Mapped[str]=mapped_column(String(80)); category:Mapped[str]=mapped_column(String(40),default='Other'); current_level:Mapped[str]=mapped_column(String(20),default='BEGINNER'); target_level:Mapped[str]=mapped_column(String(20),default='INTERMEDIATE'); start_date:Mapped[date]=mapped_column(Date,default=lambda:utcnow_naive().date()); target_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True); status:Mapped[str]=mapped_column(String(20),default='ACTIVE'); description:Mapped[str]=mapped_column(String(500),default='')
class Goal(Base):
 __tablename__='goals'
 id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); skill_id:Mapped[int]=mapped_column(ForeignKey('skills.id',ondelete='CASCADE'),index=True); title:Mapped[str]=mapped_column(String(120)); target_value:Mapped[float]=mapped_column(Float); unit:Mapped[str]=mapped_column(String(30),default='hours'); deadline:Mapped[Optional[date]]=mapped_column(Date,nullable=True); status:Mapped[str]=mapped_column(String(20),default='ACTIVE')
class Milestone(Base):
 __tablename__='milestones'
 id:Mapped[int]=mapped_column(primary_key=True); goal_id:Mapped[int]=mapped_column(ForeignKey('goals.id',ondelete='CASCADE'),index=True); title:Mapped[str]=mapped_column(String(120)); target_value:Mapped[float]=mapped_column(Float); achieved:Mapped[bool]=mapped_column(Boolean,default=False); achieved_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True)
class Practice(Base):
 __tablename__='practice_sessions'
 id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); skill_id:Mapped[int]=mapped_column(ForeignKey('skills.id',ondelete='CASCADE'),index=True); duration_minutes:Mapped[int]=mapped_column(Integer); activity:Mapped[str]=mapped_column(String(160)); notes:Mapped[str]=mapped_column(String(1000),default=''); practiced_at:Mapped[datetime]=mapped_column(DateTime,index=True,default=utcnow_naive)
class Post(Base):
 __tablename__='posts'
 id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); skill_id:Mapped[Optional[int]]=mapped_column(ForeignKey('skills.id',ondelete='SET NULL'),nullable=True); content:Mapped[str]=mapped_column(String(1000)); media_url:Mapped[Optional[str]]=mapped_column(String(500),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,index=True,default=utcnow_naive)
class Like(Base):
 __tablename__='likes'; __table_args__=(UniqueConstraint('user_id','post_id',name='uq_like_user_post'),)
 id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); post_id:Mapped[int]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE'),index=True)
class Comment(Base):
 __tablename__='comments'
 id:Mapped[int]=mapped_column(primary_key=True); post_id:Mapped[int]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE'),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); content:Mapped[str]=mapped_column(String(500)); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow_naive)
class Follow(Base):
 __tablename__='follows'; __table_args__=(UniqueConstraint('follower_id','followed_id',name='uq_follow'),)
 id:Mapped[int]=mapped_column(primary_key=True); follower_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); followed_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
Base.metadata.create_all(engine)
app=FastAPI(title='Hobby & Skills Tracker API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:8000').split(','),allow_methods=['*'],allow_headers=['*'])
app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
def get_db():
 db=SessionLocal()
 try: yield db
 finally: db.close()
def hash_password(password:str)->str:
 salt=secrets.token_bytes(16); result=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,260000)
 return base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(result).decode()
def check_password(password:str,stored:str)->bool:
 try:
  salt,digest=stored.split('$'); check=hashlib.pbkdf2_hmac('sha256',password.encode(),base64.urlsafe_b64decode(salt),260000)
  return hmac.compare_digest(base64.urlsafe_b64encode(check).decode(),digest)
 except Exception:return False
def token_for(uid:int)->str:
 enc=lambda b:base64.urlsafe_b64encode(b).rstrip(b'=').decode()
 a=enc(b'{"alg":"HS256","typ":"JWT"}'); b=enc(json.dumps({'sub':uid,'exp':int(time.time())+86400}).encode()); c=enc(hmac.new(SECRET.encode(),f'{a}.{b}'.encode(),hashlib.sha256).digest()); return f'{a}.{b}.{c}'
def db_session():
 db=SessionLocal()
 try:yield db
 finally:db.close()
def signed_in(authorization:Optional[str]=Header(None),db:Session=Depends(db_session)):
 if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Sign in required')
 try:
  a,b,c=authorization[7:].split('.'); expected=base64.urlsafe_b64encode(hmac.new(SECRET.encode(),f'{a}.{b}'.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
  if not hmac.compare_digest(c,expected):raise ValueError()
  payload=json.loads(base64.urlsafe_b64decode(b+'='*(-len(b)%4)))
  if payload['exp']<time.time():raise HTTPException(401,'Session expired')
  user=db.get(User,int(payload['sub']))
  if not user:raise ValueError()
  return user
 except HTTPException:raise
 except Exception:raise HTTPException(401,'Invalid session')
class Register(BaseModel): username:str=Field(min_length=3,max_length=30,pattern=r'^[a-zA-Z0-9_]+$'); email:str=Field(max_length=254,pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$'); name:str=Field(min_length=1,max_length=80); password:str=Field(min_length=10,max_length=128)
class Login(BaseModel):email:str=Field(max_length=254,pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$');password:str
class ProfileEdit(BaseModel):name:Optional[str]=Field(None,max_length=80);bio:Optional[str]=Field(None,max_length=500);interests:Optional[str]=Field(None,max_length=500)
class SkillIn(BaseModel):skill_name:str=Field(min_length=1,max_length=80);category:str=Field(default='Other',max_length=40);current_level:str='BEGINNER';target_level:str='INTERMEDIATE';target_date:Optional[date]=None;description:str=Field(default='',max_length=500)
class GoalIn(BaseModel):skill_id:int;title:str=Field(min_length=1,max_length=120);target_value:float=Field(gt=0);unit:str=Field(default='hours',pattern=r'^(hours|minutes)$');deadline:Optional[date]=None;milestones:list[float]=[]
class PracticeIn(BaseModel):skill_id:int;duration_minutes:int=Field(gt=0,le=1440);activity:str=Field(min_length=1,max_length=160);notes:str=Field(default='',max_length=1000);practiced_at:Optional[datetime]=None
class PostIn(BaseModel):content:str=Field(min_length=1,max_length=1000);skill_id:Optional[int]=None;media_url:Optional[str]=None
class CommentIn(BaseModel):content:str=Field(min_length=1,max_length=500)
def public(u):return {'user_id':u.id,'username':u.username,'name':u.name,'bio':u.bio,'interests':u.interests,'profile_picture':u.profile_picture,'created_at':u.created_at}
def owned_skill(db,u,sid):
 s=db.query(Skill).filter_by(id=sid,user_id=u.id).first()
 if not s:raise HTTPException(404,'Skill not found')
 return s
def skill_json(s):return {'skill_id':s.id,'skill_name':s.skill_name,'category':s.category,'current_level':s.current_level,'target_level':s.target_level,'start_date':s.start_date,'target_date':s.target_date,'status':s.status,'description':s.description}
@app.get('/api/health')
def health():return {'status':'ok'}
@app.post('/api/register',status_code=201)
def register(data:Register,db:Session=Depends(db_session)):
 email=data.email.lower().strip(); username=data.username.lower()
 if db.query(User).filter((User.email==email)|(User.username==username)).first():raise HTTPException(409,'Email or username already registered')
 u=User(username=username,email=email,name=data.name.strip(),password_hash=hash_password(data.password));db.add(u);db.commit();db.refresh(u);return {'token':token_for(u.id),'user':public(u)}
@app.post('/api/login')
def login(data:Login,db:Session=Depends(db_session)):
 u=db.query(User).filter_by(email=data.email.lower().strip()).first()
 if not u or not check_password(data.password,u.password_hash):raise HTTPException(401,'Incorrect email or password')
 return {'token':token_for(u.id),'user':public(u)}
@app.post('/api/logout')
def logout():return {'message':'Clear the bearer token in the client; token expires in 24 hours.'}
@app.get('/api/profile')
def get_profile(u:User=Depends(signed_in)):return public(u)
@app.put('/api/profile')
def update_profile(data:ProfileEdit,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 for k,v in data.model_dump(exclude_unset=True).items():setattr(u,k,v.strip() if isinstance(v,str) else v)
 db.commit();db.refresh(u);return public(u)
@app.get('/api/users/{username}')
def public_profile(username:str,db:Session=Depends(db_session)):
 u=db.query(User).filter_by(username=username.lower()).first()
 if not u:raise HTTPException(404,'User not found')
 return public(u)
@app.get('/api/skills')
def my_skills(u:User=Depends(signed_in),db:Session=Depends(db_session)):return [skill_json(s) for s in db.query(Skill).filter_by(user_id=u.id).order_by(Skill.id.desc()).all()]
@app.post('/api/skills',status_code=201)
def add_skill(data:SkillIn,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if data.current_level not in {'BEGINNER','INTERMEDIATE','ADVANCED'} or data.target_level not in {'BEGINNER','INTERMEDIATE','ADVANCED'}:raise HTTPException(422,'Invalid level')
 s=Skill(user_id=u.id,**data.model_dump());db.add(s);db.commit();db.refresh(s);return skill_json(s)
@app.get('/api/skills/{skill_id}')
def get_skill(skill_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 s=owned_skill(db,u,skill_id);return skill_json(s)
@app.put('/api/skills/{skill_id}')
def edit_skill(skill_id:int,data:SkillIn,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 s=owned_skill(db,u,skill_id)
 if data.current_level not in {'BEGINNER','INTERMEDIATE','ADVANCED'} or data.target_level not in {'BEGINNER','INTERMEDIATE','ADVANCED'}:raise HTTPException(422,'Invalid level')
 for k,v in data.model_dump().items():setattr(s,k,v)
 db.commit();db.refresh(s);return skill_json(s)
@app.delete('/api/skills/{skill_id}')
def remove_skill(skill_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 skill=owned_skill(db,u,skill_id)
 goal_ids=select(Goal.id).where(Goal.skill_id==skill.id,Goal.user_id==u.id)
 db.query(Milestone).filter(Milestone.goal_id.in_(goal_ids)).delete(synchronize_session=False)
 db.query(Goal).filter_by(skill_id=skill.id,user_id=u.id).delete(synchronize_session=False)
 db.query(Practice).filter_by(skill_id=skill.id,user_id=u.id).delete(synchronize_session=False)
 db.delete(skill);db.commit();return {'message':'Skill and its goals, milestones, and practice history deleted'}
def goal_json(g,db):
 minutes=db.query(func.coalesce(func.sum(Practice.duration_minutes),0)).filter_by(user_id=g.user_id,skill_id=g.skill_id).scalar() or 0
 current=minutes/60 if g.unit=='hours' else minutes; pct=min(100,round(current/g.target_value*100,1))
 return {'goal_id':g.id,'skill_id':g.skill_id,'title':g.title,'target_value':g.target_value,'current_value':round(current,2),'unit':g.unit,'deadline':g.deadline,'status':'COMPLETED' if pct>=100 else g.status,'progress_percent':pct}
@app.post('/api/goals',status_code=201)
def add_goal(data:GoalIn,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 owned_skill(db,u,data.skill_id)
 if any(n<=0 or n>data.target_value for n in data.milestones):raise HTTPException(422,'Milestones must be positive and at most the goal target')
 fields=data.model_dump();marks=fields.pop('milestones');g=Goal(user_id=u.id,**fields);db.add(g);db.flush()
 for n in marks:db.add(Milestone(goal_id=g.id,title=f'{n:g} {g.unit}',target_value=n))
 db.commit();db.refresh(g);return goal_json(g,db)
@app.get('/api/goals')
def get_goals(u:User=Depends(signed_in),db:Session=Depends(db_session)):return [goal_json(g,db) for g in db.query(Goal).filter_by(user_id=u.id).all()]
@app.get('/api/goals/{goal_id}/milestones')
def get_milestones(goal_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 g=db.query(Goal).filter_by(id=goal_id,user_id=u.id).first()
 if not g:raise HTTPException(404,'Goal not found')
 current=goal_json(g,db)['current_value'];ms=db.query(Milestone).filter_by(goal_id=g.id).all()
 for m in ms:
  if not m.achieved and current>=m.target_value:m.achieved=True;m.achieved_at=utcnow_naive()
 db.commit();return [{'milestone_id':m.id,'title':m.title,'target_value':m.target_value,'achieved':m.achieved,'achieved_at':m.achieved_at} for m in ms]
@app.post('/api/practice',status_code=201)
def log_practice(data:PracticeIn,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 owned_skill(db,u,data.skill_id);values=data.model_dump()
 if values['practiced_at'] and values['practiced_at'].tzinfo:values['practiced_at']=values['practiced_at'].astimezone(timezone.utc).replace(tzinfo=None)
 p=Practice(user_id=u.id,**values);db.add(p);db.commit();db.refresh(p)
 return {'session_id':p.id,'skill_id':p.skill_id,'duration_minutes':p.duration_minutes,'activity':p.activity,'notes':p.notes,'practiced_at':p.practiced_at}
@app.get('/api/practice')
def practice_history(u:User=Depends(signed_in),db:Session=Depends(db_session)):return [{'session_id':p.id,'skill_id':p.skill_id,'duration_minutes':p.duration_minutes,'activity':p.activity,'notes':p.notes,'practiced_at':p.practiced_at} for p in db.query(Practice).filter_by(user_id=u.id).order_by(Practice.practiced_at.desc()).limit(100).all()]
@app.post('/api/files/upload',status_code=201)
async def upload(file:UploadFile=File(...),u:User=Depends(signed_in)):
 allowed={'image/jpeg':('.jpg',b'\xff\xd8\xff'),'image/png':('.png',b'\x89PNG\r\n\x1a\n'),'application/pdf':('.pdf',b'%PDF-')}
 if file.content_type not in allowed:raise HTTPException(415,'Upload JPEG, PNG, or PDF')
 data=await file.read(5*1024*1024+1)
 if len(data)>5*1024*1024:raise HTTPException(413,'Maximum file size is 5 MiB')
 ext,signature=allowed[file.content_type]
 if not data.startswith(signature):raise HTTPException(415,'File content does not match declared type')
 name=f'{u.id}_{secrets.token_hex(12)}{ext}';(UPLOAD_DIR/name).write_bytes(data);return {'file_id':name,'url':f'/api/files/{name}','private':True}
@app.get('/api/files/{file_id}')
def get_file(file_id:str,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if Path(file_id).name!=file_id:raise HTTPException(404,'File not found')
 path=UPLOAD_DIR/file_id
 owned=file_id.startswith(f'{u.id}_')
 shared=db.query(Post).filter(Post.media_url==f'/api/files/{file_id}').first() is not None
 if not (owned or shared) or not path.is_file():raise HTTPException(404,'File not found')
 return FileResponse(path)
def post_json(p,author,db,viewer):
 skill=db.get(Skill,p.skill_id) if p.skill_id else None
 return {'post_id':p.id,'user':{'username':author.username,'name':author.name,'profile_picture':author.profile_picture},'skill':skill.skill_name if skill else None,'content':p.content,'media_url':p.media_url,'created_at':p.created_at,'likes_count':db.query(Like).filter_by(post_id=p.id).count(),'liked_by_me':bool(db.query(Like).filter_by(post_id=p.id,user_id=viewer).first()),'comments_count':db.query(Comment).filter_by(post_id=p.id).count()}
@app.post('/api/posts',status_code=201)
def create_post(data:PostIn,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if data.skill_id:owned_skill(db,u,data.skill_id)
 if data.media_url and not data.media_url.startswith(f'/api/files/{u.id}_'):raise HTTPException(404,'File not found')
 p=Post(user_id=u.id,**data.model_dump());db.add(p);db.commit();db.refresh(p);return post_json(p,u,db,u.id)
@app.get('/api/feed')
def feed(q:Optional[str]=None,category:Optional[str]=None,sort:str='recent',limit:int=20,offset:int=0,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if sort not in {'recent','liked'}:raise HTTPException(422,'sort must be recent or liked')
 query=db.query(Post,User).join(User,Post.user_id==User.id).outerjoin(Skill,Post.skill_id==Skill.id)
 if q:query=query.filter(Post.content.ilike(f'%{q[:80]}%'))
 if category:query=query.filter(func.lower(Skill.category)==category.lower())
 if sort=='liked':
  likes_count=select(func.count(Like.id)).where(Like.post_id==Post.id).scalar_subquery()
  query=query.order_by(likes_count.desc(),Post.created_at.desc(),Post.id.desc())
 else:query=query.order_by(Post.created_at.desc(),Post.id.desc())
 rows=query.offset(max(0,offset)).limit(min(max(1,limit),50)).all()
 return [post_json(p,a,db,u.id) for p,a in rows]
@app.delete('/api/posts/{post_id}')
def delete_post(post_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 p=db.get(Post,post_id)
 if not p:raise HTTPException(404,'Post not found')
 if p.user_id!=u.id:raise HTTPException(403,'You can delete only your own post')
 db.query(Like).filter_by(post_id=p.id).delete(synchronize_session=False)
 db.query(Comment).filter_by(post_id=p.id).delete(synchronize_session=False)
 db.delete(p);db.commit();return {'message':'Post deleted'}
@app.post('/api/posts/{post_id}/like')
def like(post_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if not db.get(Post,post_id):raise HTTPException(404,'Post not found')
 if not db.query(Like).filter_by(post_id=post_id,user_id=u.id).first():db.add(Like(post_id=post_id,user_id=u.id));db.commit()
 return {'liked':True}
@app.delete('/api/posts/{post_id}/like')
def unlike(post_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 db.query(Like).filter_by(post_id=post_id,user_id=u.id).delete();db.commit();return {'liked':False}
@app.post('/api/posts/{post_id}/comments',status_code=201)
def add_comment(post_id:int,data:CommentIn,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if not db.get(Post,post_id):raise HTTPException(404,'Post not found')
 c=Comment(post_id=post_id,user_id=u.id,content=data.content.strip());db.add(c);db.commit();db.refresh(c);return {'comment_id':c.id,'content':c.content,'username':u.username,'created_at':c.created_at}
@app.get('/api/posts/{post_id}/comments')
def comments(post_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if not db.get(Post,post_id):raise HTTPException(404,'Post not found')
 return [{'comment_id':c.id,'content':c.content,'username':db.get(User,c.user_id).username,'created_at':c.created_at} for c in db.query(Comment).filter_by(post_id=post_id).order_by(Comment.created_at).all()]
@app.delete('/api/comments/{comment_id}')
def delete_comment(comment_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 c=db.get(Comment,comment_id)
 if not c:raise HTTPException(404,'Comment not found')
 if c.user_id!=u.id:raise HTTPException(403,'You can delete only your own comment')
 db.delete(c);db.commit();return {'message':'Comment deleted'}
@app.post('/api/users/{user_id}/follow')
def follow(user_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 if u.id==user_id or not db.get(User,user_id):raise HTTPException(400,'Invalid follow target')
 if not db.query(Follow).filter_by(follower_id=u.id,followed_id=user_id).first():db.add(Follow(follower_id=u.id,followed_id=user_id));db.commit()
 return {'following':True}
@app.delete('/api/users/{user_id}/follow')
def unfollow(user_id:int,u:User=Depends(signed_in),db:Session=Depends(db_session)):
 db.query(Follow).filter_by(follower_id=u.id,followed_id=user_id).delete();db.commit();return {'following':False}
@app.get('/api/analytics/dashboard')
def analytics(u:User=Depends(signed_in),db:Session=Depends(db_session)):
 now=utcnow_naive();rows=db.query(Practice).filter_by(user_id=u.id).all();mins=sum(x.duration_minutes for x in rows);dates={x.practiced_at.date() for x in rows};today=now.date();cursor=today if today in dates else today-timedelta(days=1);streak=0
 while cursor in dates:streak+=1;cursor-=timedelta(days=1)
 longest=run=0;prev=None
 for d in sorted(dates):run=run+1 if prev and d==prev+timedelta(days=1) else 1;longest=max(longest,run);prev=d
 posts=db.query(Post).filter_by(user_id=u.id).all();gs=db.query(Goal).filter_by(user_id=u.id).all();by_skill={}
 for p in rows:by_skill[p.skill_id]=by_skill.get(p.skill_id,0)+p.duration_minutes
 return {'total_practice_hours':round(mins/60,2),'weekly_practice_hours':round(sum(p.duration_minutes for p in rows if p.practiced_at>=now-timedelta(days=7))/60,2),'monthly_practice_hours':round(sum(p.duration_minutes for p in rows if p.practiced_at>=now-timedelta(days=30))/60,2),'practice_hours_by_skill':{(db.get(Skill,k).skill_name if db.get(Skill,k) else 'Deleted skill'):round(v/60,2) for k,v in by_skill.items()},'current_streak_days':streak,'longest_streak_days':longest,'active_skills':db.query(Skill).filter_by(user_id=u.id,status='ACTIVE').count(),'goals_completed':sum(goal_json(g,db)['progress_percent']>=100 for g in gs),'active_goals':sum(goal_json(g,db)['progress_percent']<100 for g in gs),'milestones_achieved':db.query(Milestone).join(Goal).filter(Goal.user_id==u.id,Milestone.achieved.is_(True)).count(),'posts':len(posts),'likes_received':sum(db.query(Like).filter_by(post_id=p.id).count() for p in posts),'comments_received':sum(db.query(Comment).filter_by(post_id=p.id).count() for p in posts),'weekly_trend':[{'date':(today-timedelta(days=i)).isoformat(),'minutes':sum(p.duration_minutes for p in rows if p.practiced_at.date()==today-timedelta(days=i))} for i in range(6,-1,-1)]}
@app.get('/')
def home():return FileResponse(ROOT/'frontend'/'index.html')
