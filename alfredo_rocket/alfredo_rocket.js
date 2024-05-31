const { driver } = require('@rocket.chat/sdk');
const axios = require('axios')
require('dotenv').config();

// Environment Setup
const HOST = process.env.ROCKET_HOST || 'http://127.0.0.1:8000';
const USER = process.env.ROCKET_USER;
const PASS = process.env.ROCKET_PASS;
const BOTNAME = 'Alfredo';
const SSL = true;
const ROOMS = [process.env.ROCKET_ROOM];
const API_HOST = process.env.API_HOST;
const API_TOKEN = process.env.API_TOKEN;

let myUserId;

// Bot configuration
const runbot = async () => {
  const conn = await driver.connect({ host: HOST, useSsl: SSL })
  myUserId = await driver.login({ username: USER, password: PASS });
  const roomsJoined = await driver.joinRooms( ROOMS );
  console.log('joined rooms', roomsJoined);

  const subscribed = await driver.subscribeToMessages();
  console.log('subscribed');

  const msgloop = await driver.reactToMessages( processMessages );
  console.log('connected and waiting for messages');

  const sent = await driver.sendToRoom( BOTNAME + ' is listening ...', ROOMS[0]);
  console.log('Greeting message sent');
}

// Process messages
const processMessages = async(err, message, messageOptions) => {
  if (!err && messageOptions.roomParticipant) {
    if (message.u._id === myUserId) return;
    const roomname = await driver.getRoomName(message.rid);
    const headers = { 'Authorization': `Bearer ${API_TOKEN}` }
    axios
      .post(`${API_HOST}/chat`, {
        query: message.msg,
      }, 
      { headers: headers })
      .then(async res => {
        byteLength = getByteLength(res.data);
        if (byteLength > 4096) {
          attachment = {
            title: message.msg,
            text: res.data,
          }
          await driver.sendToRoomId({attachments: [attachment] }, message.rid);
        } else {
          await driver.sendToRoomId(res.data, message.rid);
        }
      })
      .catch(error => {
        console.error(error);
      });
    }
}

const getByteLength = (str) => {
  return Buffer.byteLength(str, 'utf8');
}

runbot()