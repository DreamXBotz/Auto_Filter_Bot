
import os
import re
import io
import logging
from functools import partial
from datetime import datetime
from typing import Union, BinaryIO, List, Optional, Callable

from pyrogram import StopTransmission, enums, raw, types, utils
from pyrogram.errors import FilePartMissing
from pyrogram.file_id import FileType

from pyrogram import Client

pyro_log = logging.getLogger("pyrogram")
pyro_log.setLevel(logging.WARNING)

log = logging.getLogger(__name__)

HTTP_URL_REGEX = re.compile("^https?://")

async def _resolve_video_cover(client: "Client", peer, cover: Union[str, BinaryIO, None]):
    if cover is None:
        return None

    try:
        if isinstance(cover, str):
            if os.path.isfile(cover):
                uploaded = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=peer,
                        media=raw.types.InputMediaUploadedPhoto(
                            file=await client.save_file(cover)
                        )
                    )
                )
            elif HTTP_URL_REGEX.match(cover):
                uploaded = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=peer,
                        media=raw.types.InputMediaPhotoExternal(url=cover)
                    )
                )
            else:
                return utils.get_input_media_from_file_id(cover, FileType.PHOTO).id
        else:
            uploaded = await client.invoke(
                raw.functions.messages.UploadMedia(
                    peer=peer,
                    media=raw.types.InputMediaUploadedPhoto(
                        file=await client.save_file(cover)
                    )
                )
            )

        return raw.types.InputPhoto(
            id=uploaded.photo.id,
            access_hash=uploaded.photo.access_hash,
            file_reference=uploaded.photo.file_reference
        )
    except Exception:
        log.exception("Failed to prepare video cover")
        return None

async def _get_reply_to_object(client, reply_to_message_id, reply_to_story_id, reply_to_chat_id, quote_text, parse_mode, quote_entities, message_thread_id, reply_to_monoforum_id):
    if not (reply_to_message_id or reply_to_story_id):
        return None
    reply_parameters = types.ReplyParameters(
        message_id=reply_to_message_id,
        story_id=reply_to_story_id,
        chat_id=reply_to_chat_id,
        quote=quote_text,
        quote_parse_mode=parse_mode,
        quote_entities=quote_entities
    )
    return await utils.get_reply_to(
        client=client,
        reply_parameters=reply_parameters,
        message_thread_id=message_thread_id,
        direct_messages_topic_id=reply_to_monoforum_id
    )

async def custom_send_cached_media(
        self: "Client",
        chat_id: Union[int, str],
        file_id: str,
        caption: str = "",
        parse_mode: Optional["enums.ParseMode"] = None,
        caption_entities: List["types.MessageEntity"] = None,
        has_spoiler: bool = None,
        disable_notification: bool = None,
        message_thread_id: int = None,
        reply_to_message_id: int = None,
        reply_to_story_id: int = None,
        reply_to_chat_id: Union[int, str] = None,
        reply_to_monoforum_id: Union[int, str] = None,
        quote_text: str = None,
        quote_entities: List["types.MessageEntity"] = None,
        cover: Union[str, BinaryIO] = None,
        schedule_date: datetime = None,
        protect_content: bool = None,
        allow_paid_broadcast: bool = None,
        invert_media: bool = False,
        reply_markup: Union[
            "types.InlineKeyboardMarkup",
            "types.ReplyKeyboardMarkup",
            "types.ReplyKeyboardRemove",
            "types.ForceReply"
        ] = None,
        **kwargs
    ) -> Optional["types.Message"]:
        
        peer = await self.resolve_peer(chat_id)
        reply_to = await _get_reply_to_object(self, reply_to_message_id, reply_to_story_id, reply_to_chat_id, quote_text, parse_mode, quote_entities, message_thread_id, reply_to_monoforum_id)
        
        vidcover_file = await _resolve_video_cover(self, peer, cover)
        media = utils.get_input_media_from_file_id(
            file_id,
            has_spoiler=has_spoiler,
            video_cover=vidcover_file
        )

        r = await self.invoke(
            raw.functions.messages.SendMedia(
                peer=peer,
                media=media,
                silent=disable_notification or None,
                reply_to=reply_to,
                random_id=self.rnd_id(),
                schedule_date=utils.datetime_to_timestamp(schedule_date),
                noforwards=protect_content,
                allow_paid_floodskip=allow_paid_broadcast,
                invert_media=invert_media,
                reply_markup=await reply_markup.write(self) if reply_markup else None,
                **await utils.parse_text_entities(self, caption, parse_mode, caption_entities)
            )
        )

        messages = await utils.parse_messages(client=self, messages=r)
        return messages[0] if messages else None

async def custom_send_video(
        self: "Client",
        chat_id: Union[int, str],
        video: Union[str, BinaryIO],
        caption: str = "",
        parse_mode: Optional["enums.ParseMode"] = None,
        caption_entities: List["types.MessageEntity"] = None,
        has_spoiler: bool = None,
        ttl_seconds: int = None,
        duration: int = 0,
        width: int = 0,
        height: int = 0,
        thumb: Union[str, BinaryIO] = None,
        file_name: str = None,
        supports_streaming: bool = True,
        disable_notification: bool = None,
        message_thread_id: int = None,
        business_connection_id: str = None,
        reply_to_message_id: int = None,
        reply_to_story_id: int = None,
        reply_to_chat_id: Union[int, str] = None,
        reply_to_monoforum_id: Union[int, str] = None,
        quote_text: str = None,
        quote_entities: List["types.MessageEntity"] = None,
        cover: Union[str, BinaryIO] = None,
        start_timestamp: int = None,
        schedule_date: datetime = None,
        protect_content: bool = None,
        allow_paid_broadcast: bool = None,
        message_effect_id: int = None,
        view_once: bool = None,
        invert_media: bool = None,
        reply_markup: Union[
            "types.InlineKeyboardMarkup",
            "types.ReplyKeyboardMarkup",
            "types.ReplyKeyboardRemove",
            "types.ForceReply"
        ] = None,
        progress: Callable = None,
        progress_args: tuple = (),
        **kwargs
    ) -> Optional["types.Message"]:
    
        file = None
        peer = await self.resolve_peer(chat_id)
        reply_to = await _get_reply_to_object(self, reply_to_message_id, reply_to_story_id, reply_to_chat_id, quote_text, parse_mode, quote_entities, message_thread_id, reply_to_monoforum_id)

        try:
            vidcover_file = await _resolve_video_cover(self, peer, cover)
            ttl = (1 << 31) - 1 if view_once else ttl_seconds
            
            def build_uploaded_media(saved_file, saved_thumb, name):
                return raw.types.InputMediaUploadedDocument(
                    mime_type=self.guess_mime_type(name) or "video/mp4",
                    file=saved_file,
                    ttl_seconds=ttl,
                    spoiler=has_spoiler,
                    thumb=saved_thumb,
                    attributes=[
                        raw.types.DocumentAttributeVideo(
                            supports_streaming=supports_streaming or None,
                            duration=duration,
                            w=width,
                            h=height
                        ),
                        raw.types.DocumentAttributeFilename(file_name=file_name or os.path.basename(name))
                    ],
                    video_cover=vidcover_file,
                    video_timestamp=start_timestamp
                )
            
            if isinstance(video, str):
                if os.path.isfile(video):
                    if thumb is not None: thumb = await self.save_file(thumb)
                    file = await self.save_file(video, progress=progress, progress_args=progress_args)
                    media = build_uploaded_media(file, thumb, video)
                elif HTTP_URL_REGEX.match(video):
                    media = raw.types.InputMediaDocumentExternal(
                        url=video,
                        ttl_seconds=ttl,
                        spoiler=has_spoiler,
                        video_cover=vidcover_file,
                        video_timestamp=start_timestamp
                    )
                else:
                    media = utils.get_input_media_from_file_id(
                        video,
                        FileType.VIDEO,
                        ttl_seconds=ttl,
                        has_spoiler=has_spoiler,
                        video_cover=vidcover_file,
                        video_start_timestamp=start_timestamp
                    )
            else:
                if thumb is not None: thumb = await self.save_file(thumb)
                file = await self.save_file(video, progress=progress, progress_args=progress_args)
                media = build_uploaded_media(file, thumb, getattr(video, 'name', 'video.mp4'))

            while True:
                try:
                    rpc = raw.functions.messages.SendMedia(
                        peer=peer,
                        media=media,
                        silent=disable_notification or None,
                        reply_to=reply_to,
                        random_id=self.rnd_id(),
                        schedule_date=utils.datetime_to_timestamp(schedule_date),
                        noforwards=protect_content,
                        allow_paid_floodskip=allow_paid_broadcast,
                        effect=message_effect_id,
                        invert_media=invert_media,
                        reply_markup=await reply_markup.write(self) if reply_markup else None,
                        **await utils.parse_text_entities(self, caption, parse_mode, caption_entities)
                    )
                    if business_connection_id is not None:
                        r = await self.invoke(
                            raw.functions.InvokeWithBusinessConnection(
                                connection_id=business_connection_id,
                                query=rpc
                            )
                        )
                    else:
                        r = await self.invoke(rpc)
                except FilePartMissing as e:
                    await self.save_file(video, file_id=file.id, file_part=e.value)
                else:
                    for i in r.updates:
                        if isinstance(i, (raw.types.UpdateNewMessage,
                                          raw.types.UpdateNewChannelMessage,
                                          raw.types.UpdateNewScheduledMessage,
                                          raw.types.UpdateBotNewBusinessMessage)):
                            return await types.Message._parse(
                                self, i.message,
                                {i.id: i for i in r.users},
                                {i.id: i for i in r.chats},
                                is_scheduled=isinstance(i, raw.types.UpdateNewScheduledMessage),
                                business_connection_id=business_connection_id
                            )
        except StopTransmission:
            return None


async def custom_copy(
    self: "types.Message",
    chat_id: Union[int, str],
    caption: str = None,
    parse_mode: Optional["enums.ParseMode"] = None,
    caption_entities: list["types.MessageEntity"] = None,
    has_spoiler: bool = None,
    video_cover: Optional[Union[str, "io.BytesIO"]] = None,
    disable_notification: bool = None,
    message_thread_id: int = None,
    quote_text: str = None,
    quote_entities: List["types.MessageEntity"] = None,
    reply_to_message_id: int = None,
    reply_to_chat_id: int = None,
    schedule_date: datetime = None,
    protect_content: bool = None,
    allow_paid_broadcast: bool = None,
    invert_media: bool = None,
    reply_markup: Union[
        "types.InlineKeyboardMarkup",
        "types.ReplyKeyboardMarkup",
        "types.ReplyKeyboardRemove",
        "types.ForceReply"
    ] = object,
    **kwargs
) -> Union["types.Message", List["types.Message"]]:
    if not hasattr(self, "web_page_preview"):
        self.web_page_preview = None

    if self.service:
        log.warning("Service messages cannot be copied. chat_id: %s, message_id: %s",
                    self.chat.id, self.id)
    elif self.game and not await self._client.storage.is_bot():
        log.warning("Users cannot send messages with Game media type. chat_id: %s, message_id: %s",
                    self.chat.id, self.id)
    elif self.empty:
        log.warning("Empty messages cannot be copied.")
    elif self.text:
        return await self._client.send_message(
            chat_id,
            text=self.text,
            entities=self.entities,
            parse_mode=enums.ParseMode.DISABLED,
            disable_web_page_preview=not self.web_page_preview,
            disable_notification=disable_notification,
            message_thread_id=message_thread_id,
            reply_to_message_id=reply_to_message_id,
            reply_to_chat_id=reply_to_chat_id,
            quote_text=quote_text,
            quote_entities=quote_entities,
            schedule_date=schedule_date,
            protect_content=protect_content,
            allow_paid_broadcast=allow_paid_broadcast,
            reply_markup=self.reply_markup if reply_markup is object else reply_markup
        )
    elif self.media:
        send_media = partial(
            self._client.send_cached_media,
            chat_id=chat_id,
            disable_notification=disable_notification,
            message_thread_id=message_thread_id,
            reply_to_message_id=reply_to_message_id,
            reply_to_chat_id=reply_to_chat_id,
            schedule_date=schedule_date,
            has_spoiler=has_spoiler,
            protect_content=protect_content,
            allow_paid_broadcast=allow_paid_broadcast,
            invert_media=invert_media,  # type: ignore
            reply_markup=self.reply_markup if reply_markup is object else reply_markup,
            cover=video_cover  # type: ignore
        )

        if self.photo:
            file_id = self.photo.file_id
        elif self.audio:
            file_id = self.audio.file_id
        elif self.document:
            file_id = self.document.file_id
        elif self.video:
            file_id = self.video.file_id
        elif self.animation:
            file_id = self.animation.file_id
        elif self.voice:
            file_id = self.voice.file_id
        elif self.sticker:
            file_id = self.sticker.file_id
        elif self.video_note:
            file_id = self.video_note.file_id
        elif self.contact:
            return await self._client.send_contact(
                chat_id,
                phone_number=self.contact.phone_number,
                first_name=self.contact.first_name,
                last_name=self.contact.last_name,
                vcard=self.contact.vcard,
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
                schedule_date=schedule_date,
                allow_paid_broadcast=allow_paid_broadcast,
            )
        elif self.location:
            return await self._client.send_location(
                chat_id,
                latitude=self.location.latitude,
                longitude=self.location.longitude,
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
                schedule_date=schedule_date,
                allow_paid_broadcast=allow_paid_broadcast
            )
        elif self.venue:
            return await self._client.send_venue(
                chat_id,
                latitude=self.venue.location.latitude,
                longitude=self.venue.location.longitude,
                title=self.venue.title,
                address=self.venue.address,
                foursquare_id=self.venue.foursquare_id,
                foursquare_type=self.venue.foursquare_type,
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
                schedule_date=schedule_date,
                allow_paid_broadcast=allow_paid_broadcast
            )
        elif self.poll:
            return await self._client.send_poll(
                chat_id,
                question=self.poll.question,
                options=[
                    types.InputPollOption(
                        text=opt.text
                    ) for opt in self.poll.options
                ],
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
                schedule_date=schedule_date,
                allow_paid_broadcast=allow_paid_broadcast
            )
        elif self.game:
            return await self._client.send_game(
                chat_id,
                game_short_name=self.game.short_name,
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
                allow_paid_broadcast=allow_paid_broadcast
            )
        elif self.web_page_preview:
            return await self._client.send_web_page(
                chat_id,
                url=self.web_page_preview.webpage.url,
                text=self.text,
                entities=self.entities,
                parse_mode=enums.ParseMode.DISABLED,
                show_caption_above_media=getattr(self.web_page_preview, 'show_above_text', getattr(self.web_page_preview, 'invert_media', False)),
                prefer_large_media=self.web_page_preview.force_large_media, # type: ignore
                disable_notification=disable_notification,
                message_thread_id=message_thread_id,
                reply_to_message_id=reply_to_message_id,
                reply_to_chat_id=reply_to_chat_id,
                quote_text=quote_text,
                quote_entities=quote_entities,
                schedule_date=schedule_date,
                protect_content=protect_content,
                allow_paid_broadcast=allow_paid_broadcast,
                reply_markup=self.reply_markup if reply_markup is object else reply_markup
            )
        else:
            raise ValueError("Unknown media type")

        if self.sticker or self.video_note:
            return await send_media(
                file_id=file_id,
                message_thread_id=message_thread_id,
                allow_paid_broadcast=allow_paid_broadcast
            )
        else:
            if caption is None:
                caption = self.caption or ""
                caption_entities = self.caption_entities

            return await send_media(
                file_id=file_id,
                caption=caption,
                parse_mode=parse_mode,
                caption_entities=caption_entities,
                has_spoiler=has_spoiler,
                message_thread_id=message_thread_id,
                allow_paid_broadcast=allow_paid_broadcast
            )
    else:
        raise ValueError("Can't copy this message")


async def custom_copy_message(
    self: "Client",
    chat_id: Union[int, str],
    from_chat_id: Union[int, str],
    message_id: int,
    caption: str = None,
    parse_mode: Optional["enums.ParseMode"] = None,
    caption_entities: List["types.MessageEntity"] = None,
    has_spoiler: bool = None,
    disable_notification: bool = None,
    message_thread_id: int = None,
    reply_to_message_id: int = None,
    reply_to_chat_id: int = None,
    schedule_date: datetime = None,
    protect_content: bool = None,
    allow_paid_broadcast: bool = None,
    invert_media: bool = False,
    video_cover: Optional[Union[str, "io.BytesIO"]] = None,
    reply_markup: Union[
        "types.InlineKeyboardMarkup",
        "types.ReplyKeyboardMarkup",
        "types.ReplyKeyboardRemove",
        "types.ForceReply"
    ] = None,
    **kwargs
) -> "types.Message":

    message: types.Message = await self.get_messages(from_chat_id, message_id)


    return await message.copy(
        chat_id=chat_id,
        caption=caption,
        parse_mode=parse_mode,
        caption_entities=caption_entities,
        has_spoiler=has_spoiler,
        video_cover=video_cover,  # type: ignore
        disable_notification=disable_notification,
        message_thread_id=message_thread_id,
        reply_to_message_id=reply_to_message_id,
        reply_to_chat_id=reply_to_chat_id,
        schedule_date=schedule_date,
        protect_content=protect_content,
        allow_paid_broadcast=allow_paid_broadcast,
        invert_media=invert_media,  # type: ignore
        reply_markup=reply_markup
    )

from pyrogram.methods.messages.send_cached_media import SendCachedMedia
from pyrogram.methods.messages.send_video import SendVideo
from pyrogram.methods.messages.copy_message import CopyMessage

Client.send_cached_media = custom_send_cached_media
SendCachedMedia.send_cached_media = custom_send_cached_media

Client.send_video = custom_send_video
SendVideo.send_video = custom_send_video

types.Message.copy = custom_copy

Client.copy_message = custom_copy_message
CopyMessage.copy_message = custom_copy_message


log.info("Custom Pyrogram methods have been applied.")

import asyncio
from pyrogram.types import Message
from pyrogram import StopPropagation

if not getattr(Message, "_listen_patched", False):
    Message._listen_patched = True
    Message._original_parse = Message._parse

    @staticmethod
    async def _custom_parse(client, message, users, chats, *args, **kwargs):
        msg = await Message._original_parse(client, message, users, chats, *args, **kwargs)
        if hasattr(client, "listen_futures"):
            chat_id = getattr(getattr(msg, "chat", None), "id", None)
            user_id = getattr(getattr(msg, "from_user", None), "id", None)
            key = (chat_id, user_id)
            key_chat = (chat_id, None)

            if key in client.listen_futures:
                future = client.listen_futures.pop(key)
                if not future.done():
                    future.set_result(msg)
                raise StopPropagation
                
            if key_chat in client.listen_futures:
                future = client.listen_futures.pop(key_chat)
                if not future.done():
                    future.set_result(msg)
                raise StopPropagation      
        return msg
    Message._parse = _custom_parse


async def custom_listen(self, chat_id, filters=None, timeout=60, user_id=None):
    if not hasattr(self, "listen_futures"):
        self.listen_futures = {} 
    future = asyncio.get_running_loop().create_future()
    if user_id:
        key = (chat_id, user_id)
    else:
        key = (chat_id, None)
     
    self.listen_futures[key] = future
    try:
        if timeout:
            message = await asyncio.wait_for(future, timeout=timeout)
        else:
            message = await future 
        if filters:
            if not await filters(self, message):
                return await self.listen(chat_id, filters, timeout, user_id)       
        return message
    except asyncio.TimeoutError:
        self.listen_futures.pop(key, None)
        raise

Client.listen = custom_listen
