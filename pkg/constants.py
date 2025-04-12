AQILA_EXG = 'aqila'

class RoutingKey:
  AQILA_API_TO_MONGO = 'aqila.api_to_mongo'
  AQILA_FIREBIRD_TO_API = 'aqila.firebird_to_api'
  AQILA_API_TO_FIREBIRD = 'aqila'

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_queue_messages',
            'description': 'Get messages from a queue, either by queue name or GPA code',
            'parameters': {
                'type': 'object',
                'properties': {
                    'queue_name': {
                        'type': 'string',
                        'description': 'The name of the queue to get messages from, e.g. "sync_mongo_to_postgres" or "8504"',
                        'default': None,
                    },
                    'gpa_code': {
                        'type': 'integer',
                        'description': 'GPA or client code to filter the messages',
                        'default': None,
                    },
                    'collection': {
                        'type': 'string',
                        'description': 'the collection or model to filter the messages',
                        'default': None,
                    },          
                    'limit': {
                        'type': 'integer',
                        'description': 'The number of messages to get from the queue, if not provided will get all messages',
                        'default': None,
                    },
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_queue_status',
            'description': 'Get the status of a queue',
            'parameters': {
                'type': 'object',
                'properties': {
                    'queue_name': {
                        'type': 'string',
                        'description': 'The name of the queue to get the status of, e.g. "sync_mongo_to_postgres"',
                    },
                    'without_messages': {
                        'type': 'boolean',
                        'description': 'Whether to include messages with count > 0 in the response',
                        'default': False,
                    },
                }
            },
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'summarize_queue_messages',
            'description': 'Summarize or get statistics from  messages in a queue',
            'parameters': {
                'type': 'object',
                'properties': {
                    'queue_name': {
                        'type': 'string',
                        'description': 'The name of the queue to summarize the messages from, e.g. "sync_mongo_to_postgres"',
                        'default': None,
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'The maximum number of messages to return',
                        'default': 50,
                    },
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'summarize_collections_with_error',
            'description': 'Summarize or get the status of the synchronization errors in Mongo',
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'summarize_pictures_by_status',
            'description': 'Summarize or get status for pictures in Mongo by status',
            'parameters': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'description': 'The status to filter need to be "pending", "done" or "error"',
                        'default': 'pending',
                    },
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_pull_requests',
            'description': 'List the commits from pull requests in a repository',
            'parameters': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'description': 'The status to filter need to be "closed", "all" or "open"',
                        'default': 'closed',
                    },
                    'repo_name': {
                        'type': 'string',
                        'description': 'The name of the repository to search for pull requests, e.g. "alfredo-ai"',
                        'default': '',
                    },
                    'label': {
                        'type': 'string',
                        'description': 'The label to filter the pull requests, e.g. "bug" or "enhancement"',
                        'default': '',
                    },
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_documents',
            'description': 'Search in the Pulpo knowledge base for documents that match the provided search term. - It will always have the pulpo in the text',
            'parameters': {
                'type': 'object',
                'properties': {
                    'search_term': {
                        'type': 'string',
                        'description': "The term or phrase to search for in the Pulpo knowledge base, e.g., 'how to create a new user in Pulpo'."
                    }
                },
                'required': ['search_term']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'task_helper',
            'description': 'A query search for a task in Trello, always will return a list of tasks (5) - extract the query from the string eg. "encontre informacoes sobre a tarefa offline-first the query will be "offline-first"',
            'parameters': {
                'type': 'object',
                'properties': {
                    'task_query': {
                        'type': 'string',
                        'description': 'The main query used to search for a Trello task'
                    },
                },
                'required': ['task_query'],
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'summarize_file',
            'description': 'Analyze and summarize content from a file (PDF, CSV, etc.)',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_content': {
                        'type': 'string',
                        'description': 'The extracted content from the file to be analyzed'
                    },
                    'file_type': {
                        'type': 'string',
                        'description': 'The type of file (PDF, CSV, image)',
                        'enum': ['PDF', 'CSV', 'image', 'other']
                    }
                },
                'required': ['file_content', 'file_type']
            }
        }
    }
]
