from typing import ClassVar as _ClassVar
from typing import Iterable as _Iterable
from typing import Mapping as _Mapping
from typing import Optional as _Optional
from typing import Union as _Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class JoinRequest(_message.Message):
    __slots__ = ["guildID", "channelID"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    CHANNELID_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    channelID: str
    def __init__(
        self, guildID: _Optional[str] = ..., channelID: _Optional[str] = ...
    ) -> None: ...

class PlayRequest(_message.Message):
    __slots__ = ["guildID", "channelID", "url", "position"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    CHANNELID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    channelID: str
    url: str
    position: int
    def __init__(
        self,
        guildID: _Optional[str] = ...,
        channelID: _Optional[str] = ...,
        url: _Optional[str] = ...,
        position: _Optional[int] = ...,
    ) -> None: ...

class PlayReply(_message.Message):
    __slots__ = ["tracks", "total"]
    TRACKS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    tracks: _containers.RepeatedCompositeFieldContainer[TrackData]
    total: int
    def __init__(
        self,
        tracks: _Optional[_Iterable[_Union[TrackData, _Mapping]]] = ...,
        total: _Optional[int] = ...,
    ) -> None: ...

class TrackData(_message.Message):
    __slots__ = ["title", "displayURL", "live", "position", "duration"]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DISPLAYURL_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    title: str
    displayURL: str
    live: bool
    position: _duration_pb2.Duration
    duration: _duration_pb2.Duration
    def __init__(
        self,
        title: _Optional[str] = ...,
        displayURL: _Optional[str] = ...,
        live: bool = ...,
        position: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...,
        duration: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...,
    ) -> None: ...

class GuildOnlyRequest(_message.Message):
    __slots__ = ["guildID"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    def __init__(self, guildID: _Optional[str] = ...) -> None: ...

class SeekRequest(_message.Message):
    __slots__ = ["guildID", "position"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    position: _duration_pb2.Duration
    def __init__(
        self,
        guildID: _Optional[str] = ...,
        position: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...,
    ) -> None: ...

class SeekReply(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class GetTracksRequest(_message.Message):
    __slots__ = ["guildID", "start", "end"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    start: int
    end: int
    def __init__(
        self,
        guildID: _Optional[str] = ...,
        start: _Optional[int] = ...,
        end: _Optional[int] = ...,
    ) -> None: ...

class GetTracksReply(_message.Message):
    __slots__ = ["tracks", "totalTracks", "looping", "remaining"]
    TRACKS_FIELD_NUMBER: _ClassVar[int]
    TOTALTRACKS_FIELD_NUMBER: _ClassVar[int]
    LOOPING_FIELD_NUMBER: _ClassVar[int]
    REMAINING_FIELD_NUMBER: _ClassVar[int]
    tracks: _containers.RepeatedCompositeFieldContainer[TrackData]
    totalTracks: int
    looping: bool
    remaining: _duration_pb2.Duration
    def __init__(
        self,
        tracks: _Optional[_Iterable[_Union[TrackData, _Mapping]]] = ...,
        totalTracks: _Optional[int] = ...,
        looping: bool = ...,
        remaining: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...,
    ) -> None: ...

class RemoveRequest(_message.Message):
    __slots__ = ["guildID", "position"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    position: int
    def __init__(
        self, guildID: _Optional[str] = ..., position: _Optional[int] = ...
    ) -> None: ...

class SavePlaylistRequest(_message.Message):
    __slots__ = ["guildID", "userID", "name"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    userID: str
    name: str
    def __init__(
        self,
        guildID: _Optional[str] = ...,
        userID: _Optional[str] = ...,
        name: _Optional[str] = ...,
    ) -> None: ...

class LoadPlaylistRequest(_message.Message):
    __slots__ = ["guildID", "playlistID", "channelID"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    PLAYLISTID_FIELD_NUMBER: _ClassVar[int]
    CHANNELID_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    playlistID: str
    channelID: str
    def __init__(
        self,
        guildID: _Optional[str] = ...,
        playlistID: _Optional[str] = ...,
        channelID: _Optional[str] = ...,
    ) -> None: ...

class ListPlaylistsRequest(_message.Message):
    __slots__ = ["guildID", "userID"]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    guildID: str
    userID: str
    def __init__(
        self, guildID: _Optional[str] = ..., userID: _Optional[str] = ...
    ) -> None: ...

class ListPlaylistsReply(_message.Message):
    __slots__ = ["playlists"]
    PLAYLISTS_FIELD_NUMBER: _ClassVar[int]
    playlists: _containers.RepeatedCompositeFieldContainer[Playlist]
    def __init__(
        self, playlists: _Optional[_Iterable[_Union[Playlist, _Mapping]]] = ...
    ) -> None: ...

class Playlist(_message.Message):
    __slots__ = ["id", "name", "totalTracks", "totalDuration"]
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOTALTRACKS_FIELD_NUMBER: _ClassVar[int]
    TOTALDURATION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    totalTracks: int
    totalDuration: _duration_pb2.Duration
    def __init__(
        self,
        id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        totalTracks: _Optional[int] = ...,
        totalDuration: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...,
    ) -> None: ...
