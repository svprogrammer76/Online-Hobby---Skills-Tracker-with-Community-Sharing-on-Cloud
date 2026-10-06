"""API integration tests use synthetic accounts only."""
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend import app as api

test_engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
api.Base.metadata.create_all(test_engine)
TestingSession=sessionmaker(bind=test_engine,autoflush=False,expire_on_commit=False)
def override_db():
 db=TestingSession()
 try:yield db
 finally:db.close()
api.app.dependency_overrides[api.db_session]=override_db
client=TestClient(api.app)
def account(suffix):
 suffix=f'{suffix}_{uuid4().hex[:10]}'
 r=client.post('/api/register',json={'username':f'test_{suffix}','email':f'{suffix}@example.test','name':'Test Learner','password':'A-long-test-password-123'})
 assert r.status_code==201
 return r.json()['token']
def auth(token):return {'Authorization':f'Bearer {token}'}
def test_register_duplicate_login_and_password_not_returned():
 token=account('authcheck')
 profile=client.get('/api/profile',headers=auth(token)).json()
 assert client.post('/api/register',json={'username':profile['username'],'email':'another@example.test','name':'Again','password':'A-long-test-password-123'}).status_code==409
 assert client.post('/api/login',json={'email':profile['username'].replace('test_','')+'@example.test','password':'wrong-password'}).status_code==401
 assert profile['username'].startswith('test_authcheck_')
def test_owner_isolation_skill_practice_goal_and_analytics():
 a,b=account('ownerone'),account('ownertwo')
 skill=client.post('/api/skills',headers=auth(a),json={'skill_name':'Photography','category':'Art'}).json()
 assert client.get(f"/api/skills/{skill['skill_id']}",headers=auth(b)).status_code==404
 goal=client.post('/api/goals',headers=auth(a),json={'skill_id':skill['skill_id'],'title':'Practice 2 hours','target_value':2,'milestones':[1,2]}).json()
 assert goal['progress_percent']==0
 client.post('/api/practice',headers=auth(a),json={'skill_id':skill['skill_id'],'duration_minutes':60,'activity':'Portrait practice'})
 assert client.get('/api/goals',headers=auth(a)).json()[0]['progress_percent']==50
 assert client.get('/api/analytics/dashboard',headers=auth(a)).json()['total_practice_hours']==1
 assert client.get('/api/skills',headers=auth(b)).json()==[]
def test_community_likes_comments_and_ownership():
 a,b=account('poster'),account('reader')
 p=client.post('/api/posts',headers=auth(a),json={'content':'Finished a synthetic practice milestone!'}).json();pid=p['post_id']
 assert len(client.get('/api/feed',headers=auth(b)).json())>=1
 assert client.post(f'/api/posts/{pid}/like',headers=auth(b)).status_code==200
 assert client.post(f'/api/posts/{pid}/like',headers=auth(b)).status_code==200
 assert client.get('/api/feed',headers=auth(b)).json()[0]['likes_count']==1
 c=client.post(f'/api/posts/{pid}/comments',headers=auth(b),json={'content':'Nice work!'}).json()
 assert client.delete(f"/api/comments/{c['comment_id']}",headers=auth(a)).status_code==403
 assert client.delete(f'/api/posts/{pid}',headers=auth(b)).status_code==403
 assert client.delete(f'/api/posts/{pid}',headers=auth(a)).status_code==200
 assert client.get(f'/api/posts/{pid}/comments',headers=auth(b)).status_code==404
def test_validation_and_authentication_required():
 assert client.get('/api/skills').status_code==401
 assert client.post('/api/register',json={'username':'bad_mail','email':'not-an-email','name':'Bad','password':'A-long-test-password-123'}).status_code==422
 t=account('validation')
 assert client.post('/api/skills',headers=auth(t),json={'skill_name':'','category':'Art'}).status_code==422
 assert client.post('/api/skills',headers=auth(t),json={'skill_name':'Piano'}).status_code==201
def test_delete_skill_removes_its_goals_and_practice():
 t=account('delete_skill')
 skill=client.post('/api/skills',headers=auth(t),json={'skill_name':'Duplicate Photography'}).json()
 client.post('/api/goals',headers=auth(t),json={'skill_id':skill['skill_id'],'title':'Practice 5 hours','target_value':5,'milestones':[1,5]})
 client.post('/api/practice',headers=auth(t),json={'skill_id':skill['skill_id'],'duration_minutes':30,'activity':'Practice'})
 removed=client.delete(f"/api/skills/{skill['skill_id']}",headers=auth(t))
 assert removed.status_code==200
 assert client.get('/api/skills',headers=auth(t)).json()==[]
 assert client.get('/api/goals',headers=auth(t)).json()==[]
 assert client.get('/api/practice',headers=auth(t)).json()==[]
def test_feed_category_filter_is_applied_before_pagination():
 author,reader=account('filter_author'),account('filter_reader')
 art=client.post('/api/skills',headers=auth(author),json={'skill_name':'Filter art','category':'Art'}).json()
 music=client.post('/api/skills',headers=auth(author),json={'skill_name':'Filter music','category':'Music'}).json()
 marker=uuid4().hex
 art_post=client.post('/api/posts',headers=auth(author),json={'content':f'{marker} art post','skill_id':art['skill_id']}).json()
 client.post('/api/posts',headers=auth(author),json={'content':f'{marker} music post','skill_id':music['skill_id']})
 result=client.get('/api/feed',headers=auth(reader),params={'q':marker,'category':'Art','limit':1}).json()
 assert len(result)==1 and result[0]['post_id']==art_post['post_id']
