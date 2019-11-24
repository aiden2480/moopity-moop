# Moopity Moop
The repo for my bots code 😀 See https://moopity-moop.chocolatejade42.repl.co/ for the bots website (I know, I need to get a better domain 😒)

## Issues
Right now, the biggest issue I'm having is with the website, I can't get the bloody session to retain the data that I set. I can set it fine in the `/login` route, but it always returns empty when I try to access it wtf
PS: If this message is on GitHub, it means that I somehow managed to get past this issue and the website is working fine 🎉 (I swore to myself that I would push changes as soon as I fixed this, not a minute before, not a minute after)

## Todo list
Stuff I have to do is unmarked, and stuff I'm slowly working on is marked.

Any comment with `TODO` in it anywhere throughout the repo is also something I have to do but I can't be bothered to put it on here lmao.

Any comment containing `FIXME` is something that I can't be bothered to fix right now but should definitely fix before I roll out the next batch of changes

`XXX` is just a glorified comment lmao. Just a flashy attention-grabber

Here's the stuff I have to do
- [x] Fix up whatever useless shit was going through my brain the last time I worked on this because the code looks like crap. 
- [x] Make sure `@commands.command` is the first decorator on any command
- [ ] Fix whatever fuckery black did with my beautiful syntax
- [ ] Create better command names/aliases
- [ ] Test for the `Forbidden` error that discord throws when Moopity Moop can't speak but wants to send a message
- [ ] Rip off the help command from https://github.com/nguuuquaaa/Belphegor/blob/master/belphegor/help.py because that was a cool help command
- [ ] Rip off the source command from https://github.com/nguuuquaaa/Belphegor/tree/master/belphegor/help.py#L479-L512 because that was a cool source command
- [x] Make sure all ClientSessions are referenced as `sess` not `http` because that fucks with discords internal cache
- [x] The website is literally leagues behind the bot and the bot is complete shit so I really need to get `aiohttp-session` to get its shit together and just *work*
- [ ] Fix up the README.md, maybe make it a bit *less* cancerous. I should probably sort out the `TODO list` too lol
- [ ] Consider storing data in `aiohttp-session-file` instead of `aiohttp-session` EncryptedCookieStorage?