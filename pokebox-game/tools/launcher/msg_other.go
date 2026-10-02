//go:build !windows

package main

import "fmt"

func messageBox(title, text string) { fmt.Println(title + ": " + text) }
func attachConsole()                {}
