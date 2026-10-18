
console.log('[TEST SKILL] Running custom salute skill!');
bot.chat('Sir, executing dynamic salute protocol!');
bot.setControlState('jump', true);
bot.swingArm('right');
await new Promise(r => setTimeout(r, 400));
bot.setControlState('jump', false);
return 'Salute complete';
