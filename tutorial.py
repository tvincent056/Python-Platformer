import os
import random
import math
import pygame
import LdtkJson
import json
from os import listdir
from os.path import isfile, join

class Dimmer:
    def __init__(self, keepalive=0):
        self.keepalive=keepalive
        if self.keepalive:
            self.buffer=pygame.Surface(pygame.display.get_surface().get_size())
        else:
            self.buffer=None
        self.darken_factor=0
        
    def dim(self, darken_factor=64, color_filter=(0,0,0)):
        if not self.keepalive:
            self.buffer=pygame.Surface(pygame.display.get_surface().get_size())
        self.buffer.blit(pygame.display.get_surface(),(0,0))
        if darken_factor>0:
            self.darken_factor=darken_factor
            darken=pygame.Surface(pygame.display.get_surface().get_size())
            darken.fill(color_filter)
            darken.set_alpha(darken_factor)
            # safe old clipping rectangle...
            old_clip=pygame.display.get_surface().get_clip()
            # ..blit over entire screen...
            pygame.display.get_surface().blit(darken,(0,0))
            pygame.display.flip()
            # ... and restore clipping
            pygame.display.get_surface().set_clip(old_clip)

    def undim(self):
        self.darken_factor=0
        if self.buffer is not None:
            pygame.display.get_surface().blit(self.buffer,(0,0))
            pygame.display.flip()
            if not self.keepalive:
                self.buffer=None

pygame.init()

pygame.display.set_caption("Platformer")

WIDTH, HEIGHT = 1000, 800
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))

def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


def get_block(size, type="grass_block"):
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    if type == "grass_block":
        rect = pygame.Rect(96, 0, size, size)
    elif type == "redbrick_block":
        rect = pygame.Rect(272, 64, size, size)
    surface.blit(image, (0, 0), rect)
    if size == 96:
        return pygame.transform.scale2x(surface)
    else:
        return surface


class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height, char_name):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.hearts = [Heart(10+34*x, 10) for x in range(3)]
        self.SPRITES = load_sprite_sheets("MainCharacters", char_name, 32, 32, True)

    def jump(self):
        self.y_vel = -self.GRAVITY * 8
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def make_hit(self):
        self.hit = True

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def add_damage(self):
        for i in range(len(self.hearts)-1,-1,-1):
            if self.hearts[i].state > 0:
                self.hearts[i].state -= 1
                break

    def reset_damage(self):
        for heart in self.hearts:
            heart.state = 2
    
    def get_hp(self):
        return sum([heart.state for heart in self.hearts])

    def loop(self, fps):
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0
            self.add_damage()

        self.fall_count += 1
        self.update_sprite()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count == 2:
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()
        for heart in self.hearts:
            heart.update_sprite()

    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))
        for heart in self.hearts:
            heart.draw(win)

class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))

class Heart(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size=33
        self.width = size
        self.height = size
        self.rect = pygame.Rect(x, y, size, size)
        self.sprites = []
        sprite_sheet = pygame.image.load(join("assets", "Other", "hearts.png")).convert_alpha()
        sheet_size = sprite_sheet.get_height()
        for i in range(sprite_sheet.get_width() // sheet_size):
            surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * (sheet_size+1), 0, sheet_size, sheet_size)
            surface.blit(sprite_sheet, (0, 0), rect)
            self.sprites.append(pygame.transform.smoothscale_by(surface,size/sheet_size))

        self.state = 2 #0 = empty, 1 = half, 2 = full

    def loop(self):
        self.update_sprite()

    def update_sprite(self):

        sprite_index = 2 - self.state
        self.sprite = self.sprites[sprite_index]
        self.update()

    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win):
        win.blit(self.sprite, (self.rect.x, self.rect.y))

class Block(Object):
    def __init__(self, x, y, size, type="grass_block"):
        super().__init__(x, y, size, size)
        block = get_block(size, type=type)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)

class Block2(Object):
    def __init__(self, offset_x, offset_y, size, tileset_path, tile):
        x = offset_x + tile.px[0]
        y = offset_y + tile.px[1]
        super().__init__(x, y, size, size)
        image = pygame.image.load(tileset_path).convert_alpha()
        surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
        rect = pygame.Rect(tile.src[0], tile.src[1], size, size)
        surface.blit(image, (0, 0), rect)
        block = pygame.transform.flip(surface, tile.f & 1 << 0 != 0, tile.f & 1 << 1 != 0)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)  

class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0

class Portal(Object):
    ANIMATION_DELAY = 6

    def __init__(self, x, y, width, height, dest):
        super().__init__(x, y, width, height, "portal")
        self.portal = load_sprite_sheets("Traps", "Portal", width, height)
        self.image = self.portal["glow"][0]
        # self.mask = pygame.mask.from_surface(self.image)
        self.mask = pygame.mask.Mask((0,0))
        self.animation_count = 0
        self.dest_x = dest[0]
        self.dest_y = dest[1]

    def check(self, player, up_key_is_ready, offset_x):
        keys = pygame.key.get_pressed()
        pxbuf_x = 3*player.rect.w//4
        pxbuf_y = 3*player.rect.h//4
        if up_key_is_ready and keys[pygame.K_UP]:

            if (self.rect.x - pxbuf_x < player.rect.x) and \
               (self.rect.y - pxbuf_y < player.rect.y) and \
               (self.rect.x+self.rect.w + pxbuf_x >= player.rect.x + player.rect.w) and \
               (self.rect.y+self.rect.h + pxbuf_y >= player.rect.y + player.rect.h):
                player.rect.x = self.dest_x
                player.rect.y = self.dest_y
                offset_x = self.dest_x - WIDTH//2
                up_key_is_ready = False
        return up_key_is_ready,offset_x

    def loop(self):
        sprites = self.portal["glow"]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        # self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image


def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)

    pygame.display.update()


def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()

            collided_objects.append(obj)

    return collided_objects


def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            collided_object = obj
            break

    player.move(-dx, 0)
    player.update()
    return collided_object


def handle_move(player, objects):
    keys = pygame.key.get_pressed()

    player.x_vel = 0
    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]

    for obj in to_check:
        if obj and obj.name == "fire":
            if obj.animation_name == "on":
                player.make_hit()
    

def get_pair_portal(entity_ref, level):
    entref = LdtkJson.ReferenceToAnEntityInstance.from_dict(entity_ref)
    level_layers = {layer.iid: layer for layer in level.layer_instances}
    layer = level_layers[entref.layer_iid]
    entities = {entity.iid: entity for entity in layer.entity_instances}
    entity = entities[entref.entity_iid]
    return [entity.px[0] + layer.px_total_offset_x, entity.px[1] + layer.px_total_offset_y]

def main(window):
    clock = pygame.time.Clock()
    

    block_size = 96

    with open("levels.json", 'r') as infl:
        ldtkworld = LdtkJson.ldtk_json_from_dict(json.load(infl))
    print(f"N levels: {len(ldtkworld.levels)}")
    HEIGHT = ldtkworld.levels[0].px_hei
    # WIDTH = ldtkworld.levels[0].px_wid
    print(f"N layers: {len(ldtkworld.levels[0].layer_instances)}")
    background, bg_image = get_background("Blue.png")
    tileset_defs = {ts.uid: ts for ts in ldtkworld.defs.tilesets}

    tiles = []
    for layer_instance in ldtkworld.levels[0].layer_instances:
        if layer_instance.type == "Tiles":
            tileset_def = tileset_defs[layer_instance.tileset_def_uid]
            tile_size = tileset_def.tile_grid_size
            tiles.extend([Block2(layer_instance.px_total_offset_x, layer_instance.px_total_offset_y, tile_size, layer_instance.tileset_rel_path, grid_tile)
                            for grid_tile in layer_instance.grid_tiles])
    
    #player_skin = "MaskDude"
    player_skin = "GreenMan"
    player = None
    portals = []
    player_start_x = None
    player_start_y = None
    for layer_instance in ldtkworld.levels[0].layer_instances:
        if layer_instance.type == "Entities":
            for entity in layer_instance.entity_instances:
                if entity.identifier == "PlayerStart":
                    player_start_x = entity.px[0]+layer_instance.px_total_offset_x
                    player_start_y = entity.px[1]+layer_instance.px_total_offset_y
                    player = Player(player_start_x, player_start_y, 50, 50, player_skin)
                elif "Portal" in entity.tags:
                    entity_fields = {ef.identifier: ef for ef in entity.field_instances}
                    # For now we only link portals within a level
                    portals.append(Portal(entity.px[0]+layer_instance.px_total_offset_x, entity.px[1]+layer_instance.px_total_offset_y,48,48,
                                          get_pair_portal(entity_fields["Entity_ref"].value, ldtkworld.levels[0])))

    fire = Fire(100, HEIGHT - block_size - 64, 16, 32)
    fire.on()
    # portal = Portal(1000, HEIGHT-2*block_size,48,48)
    # floor = [Block(i * block_size, HEIGHT - block_size, block_size)
    #          for i in range(-WIDTH // block_size, (WIDTH * 2) // block_size)]
    # objects = [*floor, Block(0, HEIGHT - block_size * 2, block_size),
    #            Block(block_size * 3, HEIGHT - block_size * 4, block_size),
    #            Block(block_size * 5, HEIGHT - block_size * 4, block_size/2, type="redbrick_block"),
            #    fire,
            #    portal]
    objects = [*tiles, fire, *portals]

    offset_x = 0
    scroll_area_width = 200

    run = True
    up_key_is_ready = True
    dimmer = Dimmer()
    dimmer_counter = 0
    frozen = False
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.jump_count < 2 and not frozen:
                    player.jump()
                elif event.key == pygame.K_k and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    for heart in player.hearts:
                        heart.state = 0
                elif event.key == pygame.K_RETURN:
                    if player.get_hp() == 0 and dimmer_counter > dimmer_length:
                        player.rect.x = player_start_x
                        player.rect.y = player_start_y
                        offset_x = 0
                        frozen = False
                        player.reset_damage()
                        dimmer_counter = 0

        if not frozen:
            player.loop(FPS)
            fire.loop()
            for portal in portals:
                portal.loop()
            handle_move(player, objects)
            if up_key_is_ready:
                for portal in portals:
                    up_key_is_ready,offset_x = portal.check(player,up_key_is_ready,offset_x)
            else:
                up_key_is_ready = not pygame.key.get_pressed()[pygame.K_UP]

        dimmer_length = 200
        n_dimmer_levels = 5
        if player.rect.top > HEIGHT:
            dimmer_counter += 1
            alphaval=min((1+dimmer_counter*n_dimmer_levels//dimmer_length)*255//n_dimmer_levels,255)
            if alphaval != dimmer.darken_factor:
                dimmer.dim(alphaval)
            frozen = True
            if dimmer_counter > dimmer_length:
                player.rect.x = player_start_x
                player.rect.y = player_start_y
                offset_x = 0
                frozen = False
                player.add_damage()
                health = player.get_hp()
                print(f"Hearts: {health/2}")
                if health > 0:
                    dimmer_counter = 0
        elif player.get_hp() > 0:
            dimmer.undim()        
            draw(window, background, bg_image, player, objects, offset_x)

        if player.get_hp() == 0:
            frozen = True
            if dimmer_counter <= dimmer_length:
                dimmer_counter += 1
                alphaval=min((1+dimmer_counter*n_dimmer_levels//dimmer_length)*255//n_dimmer_levels,255)
                if alphaval != dimmer.darken_factor:
                    dimmer.dim(alphaval)
            else:
                path=join("assets", "Other", "gameover.jpg")
                gameover_image=pygame.image.load(path).convert_alpha()
                window.blit(gameover_image,(300,200))
                pygame.display.update()

        if not frozen:
            if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
                    (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
                offset_x += player.x_vel

    pygame.quit()
    quit()


if __name__ == "__main__":
    main(window)
