# import pkg.rabbit as rabbit_service

# rabbit = rabbit_service.Rabbit()
# result = rabbit.get_queue_estatus()
# print(result)

# results = rabbit.get_queue_messages('sync_mongo_to_postgres')
# for result in results:
#   print(result)


# import pkg.chatbot as chatbot_service

# chatbot = chatbot_service.Chatbot()
# query = 'liste as 20 primeiras mensagens da fila sync_mongo_to_postgres'
# print(chatbot.chat(query))


import pkg.mongo as mongo_service

mongo = mongo_service.Mongo('aqila')
mongo.summarize_collections_with_error()
