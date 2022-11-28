import json
import requests
from bs4 import BeautifulSoup
from math import cos, pi, floor
import boto3

URL = "https://www.gov.il/he/departments/general/licensing-medical-psychology-scholarships"
def parse_challenge(page):
    """
    Parse a challenge given by mmi and mavat's web servers, forcing us to solve
    some math stuff and send the result as a header to actually get the page.
    This logic is pretty much copied from https://github.com/R3dy/jigsaw-rails/blob/master/lib/breakbot.rb
    """
    top = page.split('<script>')[1].split('\n')
    challenge = top[1].split(';')[0].split('=')[1]
    challenge_id = top[2].split(';')[0].split('=')[1]
    return {'challenge': challenge, 'challenge_id': challenge_id, 'challenge_result': get_challenge_answer(challenge)}


def get_challenge_answer(challenge):
    """
    Solve the math part of the challenge and get the result
    """
    arr = list(challenge)
    last_digit = int(arr[-1])
    arr.sort()
    min_digit = int(arr[0])
    subvar1 = (2 * int(arr[2])) + int(arr[1])
    subvar2 = str(2 * int(arr[2])) + arr[1]
    power = ((int(arr[0]) * 1) + 2) ** int(arr[1])
    x = (int(challenge) * 3 + subvar1)
    y = cos(pi * subvar1)
    answer = x * y
    answer -= power
    answer += (min_digit - last_digit)
    answer = str(int(floor(answer))) + subvar2
    return answer
    
    
def lambda_handler(event, context):
    s = requests.Session()
    response = s.get(URL)
    if 'X-AA-Challenge' in response.text:
       challenge = parse_challenge(response.text)
       response = s.get(URL, headers={
           'X-AA-Challenge': challenge['challenge'],
           'X-AA-Challenge-ID': challenge['challenge_id'],
           'X-AA-Challenge-Result': challenge['challenge_result']
       })

       yum = response.cookies
       response = s.get(URL, cookies=yum)
    if response.status_code == requests.codes.ok:
        soup = BeautifulSoup(response.text, 'html.parser')
        a_soup = soup.find_all('a')
        for i in a_soup:
            if(i.string == "פסיכולוגיה קלינית"):
                link = i.get('href')
                s3_client = boto3.client("s3")
                S3_BUCKET_NAME = 'psychology-updates'
                object_key = "current-link"
                file_content = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=object_key)["Body"].read()
                file_content = file_content.decode('UTF-8')
                sns_client = boto3.client('sns')
                isUpdate= False 
                msg = "בצענו בדיקה, לא נעשה עדכון מלגות בפסיכולוגיה."
                if file_content != link :
                    msg = "התעדכנו המלגות בפסיכולוגיה קלינית - קישור לקובץ: "+link
                    isUpdate= True 
                response = sns_client.publish (
                    TopicArn = 'arn:aws:sns:us-east-2:400762892327:psychology-updates-topic',
                    Message = msg
                )
                return {
                    'statusCode': 200,
                    'body': link,
                    'isUpdate': isUpdate
                }
        return {
            'statusCode': 400,
            'response.text':response.text,
            'body':a_soup
        }
    return {
        'statusCode': 404,
        'body':response.status_code
    }
