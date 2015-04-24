
import json
import datetime

def search(args, adama):
    print(json.dumps({'name': args.get('name', 'no name given')}))
    print('---')
    print(json.dumps({'localtime': datetime.datetime.now().isoformat(' ')}))