        if len(m.command) == 2 and m.command[1].startswith(('notcopy', 'sendall')):
            _, userid, verify_id, file_id = m.command[1].split("_", 3)
            user_id = int(userid)
            grp_id = temp.VERIFICATIONS.get(user_id, 0)
            settings = await get_settings(grp_id)
            verify_id_info = await db.get_verify_id_info(user_id, verify_id)
            if not verify_id_info or verify_id_info["verified"]:
                return await message.reply(script.LINK_EXPIRED_TXT)

            ist_timezone = pytz.timezone('Asia/Kolkata')
            if await db.user_verified(user_id):
                key = "third_time_verified"
            else:
                key = "second_time_verified" if await db.is_user_verified(user_id) else "last_verified"
            current_time = datetime.now(tz=ist_timezone)
            await db.update_notcopy_user(user_id, {key:current_time})
            await db.update_verify_id_info(user_id, verify_id, {"verified":True})

            if key == "third_time_verified":
                num = 3
                msg = script.THIRDT_VERIFY_COMPLETE_TEXT
            else:
                num = 2 if key == "second_time_verified" else 1
                msg = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT

            log_channel = settings.get('log') if settings and settings.get('log') else LOG_CHANNEL
            try:
                await client.send_message(log_channel, script.VERIFIED_LOG_TEXT.format(m.from_user.mention, user_id, datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y'), num))
            except Exception as e:
                logger.error(f"Failed to log verification: {e}")

            # Send Verification Complete message with the custom image & button
            is_sendall = m.command[1].startswith('sendall')
            if is_sendall:
                verifiedfiles = f"https://telegram.me/{temp.U_NAME}?start=allfiles_{grp_id}_{file_id}"
            else:
                verifiedfiles = f"https://telegram.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"

            btn_complete = [[
                InlineKeyboardButton("🫶🏻 Cʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ғɪʟᴇ 🕊", url=verifiedfiles),
            ]]
            dlt = await m.reply_photo(
                photo="https://i.ibb.co/1tDXygyb/image.webp",
                caption=msg.format(m.from_user.mention),
                reply_markup=InlineKeyboardMarkup(btn_complete),
                parse_mode=enums.ParseMode.HTML
            )

            async def _delete_msg(msg_to_delete, delay):
                await asyncio.sleep(delay)
                try:
                    await msg_to_delete.delete()
                except Exception:
                    pass

            asyncio.create_task(_delete_msg(dlt, 300))

            # Send files automatically WITHOUT stream buttons
            decoded_file_id = file_id
            if not is_sendall:
                try:
                    raw = base64.urlsafe_b64decode(file_id + "=" * (-len(file_id) % 4))
                    sep = raw.find(b"_")
                    if sep!= -1:
                        decoded_file_id = raw[sep + 1:].decode("latin1")
                except Exception:
                    pass

            filesarr = []

            if is_sendall:
                files = temp.GETALL.get(file_id)
                if not files:
                    await message.reply('<b><i>ɴᴏ ꜱᴜᴄʜ ꜰɪʟᴇ ᴇxɪꜱᴛꜱ!</b></i>')
                    return
                for file in files:
                    file_id_item = file.file_id
                    files_ = await get_file_details(file_id_item)
                    if not files_:
                        continue
                    files1 = files_[0]
                    title = clean_filename(files1.file_name)
                    cover = files1.cover
                    size = get_size(files1.file_size)
                    f_caption = files1.caption

                    DREAMX_CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION) if settings else CUSTOM_FILE_CAPTION
                    if DREAMX_CAPTION:
                        try:
                            f_caption = DREAMX_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                        except Exception as e:
                            logger.exception(e)

                    if f_caption is None:
                        f_caption = f"{clean_filename(files1.file_name)}"

                    sent_msg = await client.send_cached_media(
                        chat_id=message.from_user.id,
                        cover=cover,
                        file_id=file_id_item,
                        caption=f_caption,
                        protect_content=settings.get('file_secure', PROTECT_CONTENT) if settings else PROTECT_CONTENT
                    )
                    filesarr.append(sent_msg)
            else:
                files_ = await get_file_details(decoded_file_id)
                if not files_:
                    await message.reply('ɴᴏ ꜱᴜᴄʜ ꜰɪʟᴇ ᴇxɪꜱᴛꜱ!')
                    return
                files1 = files_[0]
                title = clean_filename(files1.file_name)
                size = get_size(files1.file_size)
                cover = files1.cover if files1.cover else None
                f_caption = files1.caption

                DREAMX_CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION) if settings else CUSTOM_FILE_CAPTION
                if DREAMX_CAPTION:
                    try:
                        f_caption = DREAMX_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                    except Exception as e:
                        logger.exception(e)

                if f_caption is None:
                    f_caption = clean_filename(files1.file_name)

                sent_msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=decoded_file_id,
                    cover=cover,
                    caption=f_caption,
                    protect_content=settings.get('file_secure', PROTECT_CONTENT) if settings else PROTECT_CONTENT
                )
                filesarr.append(sent_msg)

            # Auto-Delete Logic
            if settings and settings.get('auto_delete', True) and filesarr:
                k = await client.send_message(chat_id=message.from_user.id, text=script.DEL_MSG.format(get_time(DELETE_TIME)), parse_mode=enums.ParseMode.HTML)

                async def _delete_files(msgs, notif_msg, delay):
                    await asyncio.sleep(delay)
                    for x in msgs:
                        try:
                            await x.delete()
                        except Exception:
                            pass
                    try:
                        await notif_msg.edit_text("<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏꜱ/ꜰɪʟᴇꜱ ᴀʀᴇ ᴅᴇʟᴇᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜰᴜʟʟʏ!\nᴋɪɴᴅʟʏ ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ</b>")
                    except Exception:
                        pass

                asyncio.create_task(_delete_files(filesarr, k, DELETE_TIME))

            return
