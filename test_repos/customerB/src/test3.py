import boto3

client = boto3.client('sns')

response = client.publish(
    TopicArn='string',
    TargetArn='string',
    PhoneNumber='string',
    Message='string',
    Subject='string',
    MessageStructure='string',
    MessageAttributes={
        'string': {
            'DataType': 'string',
            'StringValue': 'string',
            'BinaryValue': b'bytes'
        }
    },
    MessageDeduplicationId='string',
    MessageGroupId='string'
    )
