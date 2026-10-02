package main

import (
	"os"
	"syscall"
	"unsafe"
)

var (
	user32   = syscall.NewLazyDLL("user32.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")
)

func messageBox(title, text string) {
	t, _ := syscall.UTF16PtrFromString(text)
	c, _ := syscall.UTF16PtrFromString(title)
	user32.NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(c)), 0x30|0x10000) // warning icon, foreground
}

// attachConsole: a GUI-subsystem exe has no console; -debug borrows the terminal it was started from
func attachConsole() {
	const attachParent = ^uintptr(0) // ATTACH_PARENT_PROCESS (-1)
	if r, _, _ := kernel32.NewProc("AttachConsole").Call(attachParent); r == 0 {
		kernel32.NewProc("AllocConsole").Call()
	}
	if f, err := os.OpenFile("CONOUT$", os.O_RDWR, 0); err == nil {
		os.Stdout, os.Stderr = f, f
	}
}
