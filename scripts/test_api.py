import json
import urllib.request

BASE='http://127.0.0.1:8000'

def post_json(path, data, token=None):
    url=BASE+path
    b=json.dumps(data).encode('utf-8')
    headers={'Content-Type':'application/json'}
    if token:
        headers['Authorization']='Bearer '+token
    req=urllib.request.Request(url, data=b, headers=headers)
    return urllib.request.urlopen(req).read().decode('utf-8')

def get(path, token=None):
    url=BASE+path
    headers={}
    if token:
        headers['Authorization']='Bearer '+token
    req=urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req).read().decode('utf-8')

if __name__=='__main__':
    try:
        print('Trying unauthenticated GET /api/gestion/inventario/categorias-producto/')
        try:
            print(get('/api/gestion/inventario/categorias-producto/'))
        except Exception as e:
            print('Unauth GET failed as expected:', e)

        print('\nLogging in...')
        resp=json.loads(post_json('/api/auth/login/', {'correo':'dev@example.test','password':'DevPass123!'}))
        token=resp.get('access') or resp.get('tokens',{}).get('access')
        print('Access token:', bool(token))

        print('\nAuthenticated GET list:')
        print(get('/api/gestion/inventario/categorias-producto/', token=token))

        print('\nCreating category...')
        new={'nombre':'Categoria Dev','descripcion':'Creada por test api','estado':True,'veterinaria':1}
        print(post_json('/api/gestion/inventario/categorias-producto/', new, token=token))

    except Exception as e:
        print('Fatal error:', e)
