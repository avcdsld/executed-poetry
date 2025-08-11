def existence():
   me = "I"
   def remember(you):
       nonlocal me
       me = you
   return me
