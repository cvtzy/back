import aiohttp
import discord


async def fetch_image_bytes(
    attachment: discord.Attachment | None = None,
    url: str | None = None,
) -> bytes:
    if attachment is not None:
        return await attachment.read()
    if url:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise ValueError(f"could not download image (http {resp.status})")
                return await resp.read()
    raise ValueError("provide either an image upload or an image url")
