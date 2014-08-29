#!/usr/bin/env python3
# encoding: utf-8
# === This file is part of Calamares - <http://github.com/calamares> ===
#
#   Copyright 2014, Pier Luigi Fiorini <pierluigi.fiorini@gmail.com>
#
#   Calamares is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Calamares is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Calamares. If not, see <http://www.gnu.org/licenses/>.

import os
import libcalamares
from libcalamares.utils import check_chroot_call

CONF_DIR = "/boot/extlinux"

def retrieve_kernels(root_mount_point):
    boot_dir = os.path.join(root_mount_point, "boot")
    kernels = []

    for filename in os.listdir(boot_dir):
        if filename[:8] in ("vmlinuz-", "bzImage-"):
            record = {
                "filename": filename,
                "version": filename[filename.index("-")+1:],
                "initramfs": None
            }
            initramfs_filename = "initramfs-%s.img" % record["version"]
            if os.path.exists(os.path.join(boot_dir, initramfs_filename)):
                record["initramfs"] = initramfs_filename
            kernels.append(record)

    return kernels

def write_conf(partitions, root_mount_point, install_path):
    plymouth_bin = os.path.join(root_mount_point, "usr/bin/plymouth")
    use_splash = ""
    swap_uuid = ""
    root_device = ""

    if os.path.exists(plymouth_bin):
        use_splash = "splash"

    for partition in partitions:
        if partition["mountPoint"] == "/":
            root_device = partition["device"]
        if partition["fs"] == "linuxswap":
            swap_uuid = partition["uuid"]

    kernel_cmdline = "root=%s ro " % root_device
    if swap_uuid != "":
        kernel_cmdline += "resume=UUID=%s quiet %s" % (swap_uuid, use_splash)
    else:
        kernel_cmdline += "quiet %s" % use_splash

    cfg_distributor = libcalamares.job.configuration["distributor"]
    cfg_prompt = libcalamares.job.configuration["prompt"]
    cfg_timeout = libcalamares.job.configuration["timeout"]
    cfg_menu = libcalamares.job.configuration["menu"]
    cfg_background = libcalamares.job.configuration["background"]

    conf_dir = root_mount_point + CONF_DIR
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    conf_file = conf_dir + "/extlinux.conf"
    f = open(conf_file, "w")
    f.write("# extlinux.conf - Generated by Calamares\n\n")
    f.write("prompt %d\n" % cfg_prompt)
    f.write("timeout %d\n" % cfg_timeout)
    if cfg_menu:
        f.write("default %s\n\n" % cfg_menu)
    f.write("menu autoboot Starting...\n")
    f.write("menu hidden\n")
    if cfg_background:
        check_chroot_call(["cp", cfg_background, os.path.join(CONF_DIR, os.path.basename(cfg_background))])
        f.write("menu background %s\n" % os.path.basename(cfg_background))
    f.write("menu title Welcome to %s!\n\n" % cfg_distributor)

    kernels = retrieve_kernels(root_mount_point)
    i = 0
    for kernel in kernels:
        print("Create entry %d for kernel %s" % (i, kernel["version"]))

        f.write("label linux%d\n" % i)
        f.write("\tmenu label %s (%s)\n" % (cfg_distributor, kernel["version"]))
        f.write("\tkernel %s\n" % kernel["filename"])
        if kernel["initramfs"]:
            f.write("\tappend initrd=%s %s\n" % (kernel["initramfs"], kernel_cmdline))
        else:
            f.write("\tappend %s\n" % kernel_cmdline)
        f.write("\tmenu default\n\n")

        kernel_filename = root_mount_point + CONF_DIR + "/" kernel["filename"])
        if os.path.exists(kernel_filename) or os.path.lexists(kernel_filename):
            os.remove(kernel_filename)
        os.symlink("../%s" % kernel["filename"], kernel_filename)
        if kernel["initramfs"]:
            initramfs_filename = root_mount_point + CONF_DIR + "/" kernel["initramfs"])
            if os.path.exists(initramfs_filename) or os.path.lexists(initramfs_filename):
                os.remove(initramfs_filename)
            os.symlink("../%s" % kernel["initramfs"], initramfs_filename)

        i += 1

    f.close()    

def run():
    partitions = libcalamares.globalstorage.value("partitions")
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    install_path = libcalamares.globalstorage.value("bootLoader")["installPath"]
    write_conf(partitions, root_mount_point, install_path)
    return None
