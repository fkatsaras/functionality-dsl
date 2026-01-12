python -c "import jwt, time; SECRET='ecommerce-secret-key-change-in-production'; \
print('Customer:', jwt.encode({'sub':'customer1','roles':['customer'],'exp':int(time.time())+3600}, SECRET, algorithm='HS256')); \
print('Warehouse:', jwt.encode({'sub':'warehouse1','roles':['warehouse'],'exp':int(time.time())+3600}, SECRET, algorithm='HS256'))"
